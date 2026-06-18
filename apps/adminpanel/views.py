"""Admin panel APIs: auth, dashboard, settings, activity, users."""
import json
import os
from urllib import error as urlerror, request as urlrequest

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import generics, mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.inquiries.models import Inquiry
from apps.listings.models import Listing
from apps.users.views import UserAdminViewSet  # noqa: F401  (re-exported in urls)

from .dealer_offers import DEFAULT_DEALER_OFFER_CAMPAIGN, merge_dealer_offer_campaign
from .models import ActivityLog, Admin, AppSettings
from .permissions import IsAdminOperator
from .serializers import (
    ActivityLogSerializer,
    AdminLoginSerializer,
    AdminSerializer,
    AppSettingsSerializer,
    admin_jwt_tokens,
    staff_jwt_tokens,
)

User = get_user_model()


ASSISTANT_CONTEXT = """
You are Old Car Bazar's helpful AI assistant for India.
Answer in simple Hindi/Hinglish by default, unless the user asks in English.
Help users with buying used cars, selling a car, pricing, valuation, EMI,
loan eligibility, RC transfer, insurance, test drives, dealer discovery,
saved cars, subscriptions, featured/boosted listings, and platform support.
Keep answers concise, practical, and friendly. Do not claim a listing is
verified unless the platform data or user says it is. For legal/finance
matters, give general guidance and suggest checking official documents or
contacting support for final confirmation.
"""

# Tried in order until one model responds (older names kept as fallback).
GEMINI_MODEL_FALLBACKS = (
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
)


def _assistant_rule_reply(question: str) -> str | None:
    """Fast answers that do not need the LLM (support contact, etc.)."""
    q = question.lower()
    settings = AppSettings.singleton()
    contact_triggers = (
        "contact number",
        "phone number",
        "mobile number",
        "call kare",
        "call kar",
        "support number",
        "helpline",
        "customer care",
        "contact",
        "email",
        "support",
    )
    if any(trigger in q for trigger in contact_triggers):
        return (
            f"Old Car Bazar support:\n"
            f"Phone: {settings.support_phone}\n"
            f"Email: {settings.support_email}\n"
            f"Website par Contact / Help section bhi dekh sakte ho."
        )
    return None


def _gemini_key_hint(api_key: str) -> str | None:
    """Warn when the env key looks like the wrong Google credential type."""
    if api_key.startswith("AQ."):
        return (
            "Gemini API key galat type ki lag rahi hai (GCP service key). "
            "Google AI Studio se nayi key banayein — https://aistudio.google.com/app/apikey — "
            "key `AIza...` se start honi chahiye. Render env me GEMINI_API_KEY update karein."
        )
    if not api_key.startswith("AIza"):
        return (
            "Gemini API key invalid lag rahi hai. "
            "https://aistudio.google.com/app/apikey se nayi key lein (AIza... format) "
            "aur hosting env me GEMINI_API_KEY set karein."
        )
    return None


def _gemini_models_to_try() -> list[str]:
    preferred = os.environ.get("GEMINI_MODEL", "").strip()
    models: list[str] = []
    if preferred:
        models.append(preferred)
    for name in GEMINI_MODEL_FALLBACKS:
        if name not in models:
            models.append(name)
    return models


def _call_gemini(api_key: str, question: str) -> tuple[str | None, str | None]:
    """Call Gemini generateContent. Returns (reply, error_message)."""
    payload = {
        "systemInstruction": {
            "parts": [{"text": ASSISTANT_CONTEXT.strip()}],
        },
        "contents": [
            {"role": "user", "parts": [{"text": question}]},
        ],
        "generationConfig": {
            "temperature": 0.35,
            "maxOutputTokens": 450,
        },
    }
    body = json.dumps(payload).encode("utf-8")
    last_error: str | None = None
    models = _gemini_models_to_try()

    for model in models:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent"
        )
        req = urlrequest.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": api_key,
            },
            method="POST",
        )
        try:
            with urlrequest.urlopen(req, timeout=25) as res:
                data = json.loads(res.read().decode("utf-8"))
        except urlerror.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace")
            try:
                err_json = json.loads(err_body)
                last_error = str(err_json.get("error", {}).get("message", err_body))
            except json.JSONDecodeError:
                last_error = err_body[:240] or str(exc)
            # Model missing / deprecated — try the next one.
            if exc.code in (400, 404) and model != models[-1]:
                continue
            break
        except (urlerror.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = str(exc)
            break
        else:
            candidates = data.get("candidates") or []
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                reply = "\n".join(
                    part.get("text", "")
                    for part in parts
                    if isinstance(part, dict)
                ).strip()
                if reply:
                    return reply, None
            last_error = "Empty response from Gemini."

    return None, last_error


class AssistantView(generics.GenericAPIView):
    """POST /api/v1/assistant/ — AI help assistant for website + mobile app."""

    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        question = str(request.data.get("message") or "").strip()
        if not question:
            return Response(
                {"reply": "Please type your question first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        rule_reply = _assistant_rule_reply(question)
        if rule_reply:
            return Response({"reply": rule_reply, "configured": True})

        api_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not api_key:
            return Response({
                "reply": (
                    "AI assistant ready hai, bas backend me GEMINI_API_KEY "
                    "set karna baaki hai. Tab tak aap Buy, Sell, EMI, Loan, "
                    "RC Transfer ya Support se related question pooch sakte ho."
                ),
                "configured": False,
            })

        key_hint = _gemini_key_hint(api_key)
        if key_hint:
            return Response({"reply": key_hint, "configured": False})

        reply, gemini_error = _call_gemini(api_key, question)
        if reply:
            return Response({"reply": reply, "configured": True})

        from django.conf import settings as django_settings

        detail = ""
        if django_settings.DEBUG and gemini_error:
            detail = f" ({gemini_error})"

        return Response(
            {
                "reply": (
                    "AI service abhi respond nahi kar pa raha. "
                    "Thodi der baad try karein ya support se contact karein."
                    f"{detail}"
                )
            },
            status=status.HTTP_502_BAD_GATEWAY,
        )


class AdminLoginView(generics.GenericAPIView):
    """POST /api/v1/admin-panel/login → admin JWT pair."""
    serializer_class = AdminLoginSerializer
    permission_classes = (permissions.AllowAny,)

    def post(self, request):
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        staff_user = ser.validated_data.get("staff_user")
        if staff_user is not None:
            staff_user.last_login_at = timezone.now()
            staff_user.save(update_fields=["last_login_at"])
            tokens = staff_jwt_tokens(staff_user)
            return Response({
                **tokens,
                "admin": {
                    "id": str(staff_user.id),
                    "name": staff_user.name,
                    "email": staff_user.email,
                    "role": "super-admin" if staff_user.is_superuser else "moderator",
                    "avatar_url": staff_user.avatar_url,
                    "last_login_at": staff_user.last_login_at,
                    "created_at": staff_user.date_joined,
                },
            })

        admin: Admin = ser.validated_data["admin"]
        admin.last_login_at = timezone.now()
        admin.save(update_fields=["last_login_at"])
        ActivityLog.objects.create(
            actor_admin=admin,
            type="admin-login",
            message=f"{admin.name} signed in",
            target=admin.email,
        )
        tokens = admin_jwt_tokens(admin)
        return Response({**tokens, "admin": AdminSerializer(admin).data})


class AdminMeView(generics.GenericAPIView):
    """GET /api/v1/admin-panel/me → currently signed-in admin."""
    permission_classes = (IsAdminOperator,)
    serializer_class = AdminSerializer

    def get(self, request):
        admin = getattr(request, "admin", None)
        # Django superuser shortcut (no separate Admin row required).
        if not admin and request.user.is_authenticated and request.user.is_staff:
            return Response({
                "id": str(request.user.id),
                "name": request.user.name,
                "email": request.user.email,
                "role": "super-admin",
                "avatar_url": "",
                "last_login_at": request.user.last_login_at,
                "created_at": request.user.date_joined,
            })
        return Response(AdminSerializer(admin).data)


class DashboardStatsView(generics.GenericAPIView):
    """GET /api/v1/admin-panel/dashboard"""
    permission_classes = (IsAdminOperator,)

    def get(self, request):
        from apps.listings.serializers import ListingSerializer  # local import to avoid cycles

        listings_qs = Listing.objects.all()
        inquiries_qs = Inquiry.objects.all()

        totals = {
            "listings": {
                "total": listings_qs.count(),
                "pending": listings_qs.filter(moderation="pending").count(),
                "featured": listings_qs.filter(featured=True).count(),
                "rejected": listings_qs.filter(moderation="rejected").count(),
            },
            "inquiries": {
                "total": inquiries_qs.count(),
                "new": inquiries_qs.filter(status="new").count(),
            },
            "users": {
                "total": User.objects.count(),
                "buyers": User.objects.filter(role__in=("buyer", "both")).count(),
                "sellers": User.objects.filter(role__in=("seller", "both")).count(),
                "blocked": User.objects.filter(status="blocked").count(),
            },
        }

        by_brand = list(
            listings_qs.values("brand")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )
        by_fuel = list(
            listings_qs.values("fuel").annotate(count=Count("id")).order_by("-count")
        )
        by_city = list(
            listings_qs.values("location").annotate(count=Count("id")).order_by("-count")[:10]
        )

        recent_listings = Listing.objects.order_by("-created_at")[:5]
        recent_activity = ActivityLog.objects.order_by("-created_at")[:10]

        return Response({
            "totals": totals,
            "breakdown": {
                "byBrand": by_brand,
                "byFuel": by_fuel,
                "byCity": by_city,
            },
            "recentListings": ListingSerializer(recent_listings, many=True).data,
            "recentActivity": ActivityLogSerializer(recent_activity, many=True).data,
        })


class AdminPaymentsView(generics.GenericAPIView):
    """GET /api/v1/admin-panel/payments/

    All money flowing through the platform, for the admin panel:
      • subscriptions — every Pro plan activation (with Razorpay txn ids)
      • boosts        — every paid listing boost (with Razorpay txn ids)
    """
    permission_classes = (IsAdminOperator,)

    def get(self, request):
        from apps.subscriptions.models import Subscription
        from apps.subscriptions.plans import get_plan
        from apps.listings.models import ListingBoostOrder

        sub_rows = []
        subscriptions = (
            Subscription.objects
            .select_related("user", "razorpay_order")
            .order_by("-created_at")
        )
        for sub in subscriptions:
            plan = get_plan(sub.plan)
            rzp = getattr(sub, "razorpay_order", None)
            sub_rows.append({
                "id": str(sub.id),
                "user_name": sub.user.name if sub.user_id else "—",
                "user_phone": sub.user.phone if sub.user_id else "",
                "user_email": (sub.user.email or "") if sub.user_id else "",
                "plan": sub.plan,
                "plan_name": plan.name if plan else sub.plan,
                "amount_inr": sub.amount_inr,
                "status": sub.status,
                "provider": sub.provider,
                "razorpay_order_id": rzp.razorpay_order_id if rzp else "",
                "razorpay_payment_id": (
                    rzp.razorpay_payment_id if rzp else sub.provider_payment_id
                ),
                "receipt": rzp.receipt if rzp else f"ocb_sub_{sub.id.hex[:12]}",
                "invoice_number": (
                    f"OCB-{sub.started_at:%Y%m%d}-"
                    f"{str(sub.id).split('-')[0].upper()}"
                ),
                "started_at": sub.started_at,
                "expires_at": sub.expires_at,
                "created_at": sub.created_at,
            })

        boost_rows = []
        boosts = (
            ListingBoostOrder.objects
            .select_related("user", "listing")
            .order_by("-created_at")
        )
        for order in boosts:
            boost_rows.append({
                "id": str(order.id),
                "user_name": order.user.name if order.user_id else "—",
                "user_phone": order.user.phone if order.user_id else "",
                "user_email": (order.user.email or "") if order.user_id else "",
                "listing_id": str(order.listing_id) if order.listing_id else "",
                "listing_title": order.listing.title if order.listing_id else "—",
                "package": order.package,
                "duration_days": order.duration_days,
                "amount_inr": order.amount_inr,
                "status": order.status,
                "razorpay_order_id": order.razorpay_order_id,
                "razorpay_payment_id": order.razorpay_payment_id,
                "receipt": order.receipt,
                "invoice_number": f"OCB-BOOST-{str(order.id).split('-')[0].upper()}",
                "boosted_until": order.boosted_until,
                "created_at": order.created_at,
            })

        sub_revenue = sum(r["amount_inr"] for r in sub_rows)
        boost_revenue = sum(
            r["amount_inr"] for r in boost_rows if r["status"] == "paid"
        )

        return Response({
            "subscriptions": sub_rows,
            "boosts": boost_rows,
            "summary": {
                "subscriptions_count": len(sub_rows),
                "subscriptions_revenue": sub_revenue,
                "boosts_count": len([r for r in boost_rows if r["status"] == "paid"]),
                "boosts_revenue": boost_revenue,
                "total_revenue": sub_revenue + boost_revenue,
            },
        })


class DealerOffersView(APIView):
    """GET / PUT  /api/v1/admin-panel/dealer-offers/

    Manage the dealer launch-offer campaign and list active grants.
    """

    permission_classes = (IsAdminOperator,)

    def get(self, request):
        from apps.subscriptions.models import Subscription
        from apps.subscriptions.plans import DEALER_TRIAL_PLANS, get_plan
        from apps.subscriptions.services import count_active_listings

        settings = AppSettings.singleton()
        campaign = merge_dealer_offer_campaign(settings.dealer_offer)

        plans = [p.to_dict() for p in DEALER_TRIAL_PLANS.values()]

        now = timezone.now()
        active_qs = (
            Subscription.objects.filter(
                plan__in=DEALER_TRIAL_PLANS.keys(),
                status=Subscription.Status.ACTIVE,
                expires_at__gt=now,
            )
            .select_related("user")
            .order_by("-expires_at")
        )
        active_grants = []
        for sub in active_qs:
            plan = get_plan(sub.plan)
            user = sub.user
            active_grants.append({
                "subscription_id": str(sub.id),
                "user_id": str(user.id) if user else "",
                "user_name": user.name if user else "—",
                "user_phone": user.phone if user else "",
                "user_email": (user.email or "") if user else "",
                "user_city": user.city if user else "",
                "plan": sub.plan,
                "plan_name": plan.name if plan else sub.plan,
                "listings_count": count_active_listings(user) if user else 0,
                "started_at": sub.started_at,
                "expires_at": sub.expires_at,
                "provider": sub.provider,
            })

        grants_used = len(active_grants)
        max_grants = int(campaign.get("max_grants") or 0)

        return Response({
            "campaign": campaign,
            "plans": plans,
            "active_grants": active_grants,
            "stats": {
                "grants_used": grants_used,
                "max_grants": max_grants,
                "slots_remaining": max(max_grants - grants_used, 0) if max_grants else None,
            },
        })

    def put(self, request):
        settings = AppSettings.singleton()
        incoming = request.data if isinstance(request.data, dict) else {}
        merged = merge_dealer_offer_campaign({
            **(settings.dealer_offer or {}),
            **incoming,
        })
        settings.dealer_offer = merged
        settings.save(update_fields=["dealer_offer", "updated_at"])

        ActivityLog.objects.create(
            actor_admin=getattr(request, "admin", None),
            type="dealer-offer-updated",
            message="Dealer offer campaign updated",
            metadata={"enabled": merged.get("enabled"), "default_plan_code": merged.get("default_plan_code")},
        )

        return Response({"campaign": merged})


class DealerOfferRevokeView(APIView):
    """POST /api/v1/admin-panel/dealer-offers/<sub_id>/revoke/

    Immediately cancel an active dealer trial offer.
    """

    permission_classes = (IsAdminOperator,)

    def post(self, request, sub_id):
        from apps.subscriptions.models import Subscription
        from apps.subscriptions.plans import DEALER_TRIAL_PLANS, get_plan

        sub = (
            Subscription.objects.filter(
                id=sub_id,
                plan__in=DEALER_TRIAL_PLANS.keys(),
            )
            .select_related("user")
            .first()
        )
        if not sub:
            return Response(
                {"detail": "Dealer offer not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if sub.status != Subscription.Status.ACTIVE:
            return Response(
                {"detail": "This offer is already inactive."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        admin = getattr(request, "admin", None)
        actor_name = admin.name if admin else "admin"
        sub.status = Subscription.Status.CANCELLED
        sub.expires_at = now
        sub.notes = (
            f"{sub.notes}\nRevoked by {actor_name} via admin panel at {now:%Y-%m-%d %H:%M}"
        ).strip()
        sub.save(update_fields=["status", "expires_at", "notes", "updated_at"])

        plan = get_plan(sub.plan)
        user = sub.user
        ActivityLog.objects.create(
            actor_admin=admin,
            type="dealer-offer-revoked",
            message=f"Revoked {plan.name if plan else sub.plan} for {user.name if user else 'dealer'}",
            target=str(user.id) if user else str(sub.id),
            metadata={
                "subscription_id": str(sub.id),
                "plan": sub.plan,
                "user_phone": user.phone if user else "",
            },
        )

        return Response({
            "ok": True,
            "subscription_id": str(sub.id),
            "user_id": str(user.id) if user else "",
            "status": sub.status,
        })


class AppSettingsView(generics.RetrieveUpdateAPIView):
    """GET / PATCH  /api/v1/admin-panel/settings"""
    serializer_class = AppSettingsSerializer
    permission_classes = (IsAdminOperator,)

    def get_object(self):
        return AppSettings.singleton()

    def perform_update(self, serializer):
        serializer.save()
        ActivityLog.objects.create(
            actor_admin=getattr(self.request, "admin", None),
            type="settings-updated",
            message="Platform settings updated",
        )


class LoanToolsContentView(generics.GenericAPIView):
    """GET /api/v1/loan-tools/content/ — public Loan & Tools copy for the storefront."""

    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        settings_row = AppSettings.singleton()
        return Response({"content": settings_row.loan_tools_content})


class AdsView(generics.GenericAPIView):
    """GET /api/v1/ads/ — public ad banners for the website + mobile app.

    Only enabled ads are returned. Optional query params let a client narrow
    results without doing the filtering itself:
      • ?platform=web|app   → only ads targeting that platform (or "both")
      • ?page=home|all|...  → only ads whose target pages include this page
    """

    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        ads = AppSettings.singleton().ads or []
        if not isinstance(ads, list):
            ads = []

        enabled = [ad for ad in ads if isinstance(ad, dict) and ad.get("enabled")]

        platform = request.query_params.get("platform")
        if platform:
            enabled = [
                ad for ad in enabled
                if (ad.get("platform") or "both") in (platform, "both")
            ]

        page = request.query_params.get("page")
        if page:
            enabled = [
                ad for ad in enabled
                if page in (ad.get("pages") or []) or "all" in (ad.get("pages") or [])
            ]

        return Response({"ads": enabled})


class ActivityLogViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """GET /api/v1/admin-panel/activity/"""
    queryset = ActivityLog.objects.select_related("actor_admin").all()
    serializer_class = ActivityLogSerializer
    permission_classes = (IsAdminOperator,)
    filterset_fields = ("type",)
    ordering = ("-created_at",)
