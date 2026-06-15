"""Subscription API.

Endpoints (all under `/api/v1/subscriptions/`):

    GET  /plans/      Public list of plan options (free + paid).
    GET  /status/     Auth required. Current user's plan + quota usage.
    POST /create-order/     Auth required. Create Razorpay checkout order.
    POST /verify-payment/   Auth required. Verify Razorpay signature and
                             activate subscription.
    POST /webhook/          Public Razorpay callback, signature verified.
    POST /activate/         Auth required. Demo/manual activation fallback.
    GET  /mine/       Auth required. History of this user's paid rows.
"""
import hashlib
import hmac
import json
import uuid

from django.conf import settings as dj_settings
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.billing.gst import (
    GST_RATE_PERCENT,
    SELLER_GSTIN,
    compute_gst,
    seller_invoice_block,
)

from .models import RazorpayOrder, Subscription
from .plans import ALL_PLANS, get_plan
from .serializers import (
    ActivateSubscriptionSerializer,
    CreateRazorpayOrderSerializer,
    PlanSerializer,
    RazorpayOrderSerializer,
    SubscriptionSerializer,
    SubscriptionStatusSerializer,
    VerifyRazorpayPaymentSerializer,
)
from .services import (
    activate_subscription,
    can_publish,
    get_active_subscription,
)


def _allow_demo() -> bool:
    """Demo activation is on by default in DEBUG, off in production
    unless the operator opts in explicitly."""
    return bool(
        getattr(
            dj_settings,
            "SUBSCRIPTION_ALLOW_DEMO_ACTIVATION",
            dj_settings.DEBUG,
        )
    )


def _razorpay_configured() -> bool:
    return bool(dj_settings.RAZORPAY_KEY_ID and dj_settings.RAZORPAY_KEY_SECRET)


def _razorpay_client():
    """Return an authenticated Razorpay client or raise a clear error."""
    if not _razorpay_configured():
        raise RuntimeError("Razorpay keys are not configured.")
    try:
        import razorpay
    except ImportError as exc:  # pragma: no cover - dependency/runtime guard
        raise RuntimeError("Razorpay SDK is not installed.") from exc
    return razorpay.Client(
        auth=(dj_settings.RAZORPAY_KEY_ID, dj_settings.RAZORPAY_KEY_SECRET)
    )


def _gateway_not_configured_response():
    return Response(
        {
            "detail": (
                "Payments are not configured yet. Add Razorpay keys "
                "on the backend and redeploy."
            ),
            "code": "gateway_not_configured",
        },
        status=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


class PlansView(APIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        data = [PlanSerializer(p.to_dict()).data for p in ALL_PLANS.values()]
        return Response({"plans": data})


class SubscriptionStatusView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        allowed, info = can_publish(request.user)
        sub = get_active_subscription(request.user)
        info["started_at"] = sub.started_at if sub else None
        info["expires_at"] = sub.expires_at if sub else None
        info["can_publish"] = allowed
        return Response(SubscriptionStatusSerializer(info).data)


class CreateRazorpayOrderView(APIView):
    """Create a Razorpay order for the selected paid plan."""

    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        ser = CreateRazorpayOrderSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        plan = get_plan(ser.validated_data["plan"])
        if not plan or plan.code == "free":
            return Response(
                {"detail": "Unknown or non-purchasable plan."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if plan.price_inr <= 0:
            return Response(
                {"detail": "This plan does not require payment."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            client = _razorpay_client()
        except RuntimeError:
            return _gateway_not_configured_response()

        customer_gstin = ser.validated_data.get("customer_gstin", "")
        base_inr, gst_inr, total_inr = compute_gst(plan.price_inr)

        receipt = f"ocb_{request.user.id.hex[:12]}_{uuid.uuid4().hex[:12]}"
        amount_paise = total_inr * 100
        payload = {
            "amount": amount_paise,
            "currency": "INR",
            "receipt": receipt,
            "notes": {
                "user_id": str(request.user.id),
                "plan": plan.code,
                "product": "old-car-bazar-subscription",
                "gst_inr": str(gst_inr),
                "customer_gstin": customer_gstin,
            },
        }

        try:
            order = client.order.create(data=payload)
        except Exception as exc:  # pragma: no cover - provider/network error
            return Response(
                {
                    "detail": f"Could not create Razorpay order: {exc}",
                    "code": "razorpay_order_failed",
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        RazorpayOrder.objects.create(
            user=request.user,
            plan=plan.code,
            amount_inr=total_inr,
            base_inr=base_inr,
            gst_inr=gst_inr,
            customer_gstin=customer_gstin,
            razorpay_order_id=order["id"],
            receipt=receipt,
            raw_response=order,
        )

        data = {
            "key_id": dj_settings.RAZORPAY_KEY_ID,
            "order_id": order["id"],
            "amount": amount_paise,
            "amount_inr": total_inr,
            "base_inr": base_inr,
            "gst_inr": gst_inr,
            "gst_rate": GST_RATE_PERCENT,
            "seller_gstin": SELLER_GSTIN,
            "customer_gstin": customer_gstin,
            "currency": "INR",
            "plan": plan.to_dict(),
            "name": request.user.name,
            "email": request.user.email or "",
            "contact": request.user.phone,
        }
        return Response(RazorpayOrderSerializer(data).data, status=status.HTTP_201_CREATED)


class VerifyRazorpayPaymentView(APIView):
    """Verify Razorpay checkout response and activate the subscription."""

    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        ser = VerifyRazorpayPaymentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        order = (
            RazorpayOrder.objects
            .select_related("subscription")
            .filter(
                user=request.user,
                razorpay_order_id=data["razorpay_order_id"],
            )
            .first()
        )
        if not order:
            return Response(
                {"detail": "Payment order not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if order.status == RazorpayOrder.Status.PAID and order.subscription:
            return Response(
                SubscriptionSerializer(order.subscription).data,
                status=status.HTTP_200_OK,
            )

        plan = get_plan(order.plan)
        if not plan or plan.code == "free":
            return Response(
                {"detail": "Invalid subscription plan for this order."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            client = _razorpay_client()
        except RuntimeError:
            return _gateway_not_configured_response()

        signature_payload = {
            "razorpay_order_id": data["razorpay_order_id"],
            "razorpay_payment_id": data["razorpay_payment_id"],
            "razorpay_signature": data["razorpay_signature"],
        }
        try:
            client.utility.verify_payment_signature(signature_payload)
            payment = client.payment.fetch(data["razorpay_payment_id"])
        except Exception as exc:
            order.status = RazorpayOrder.Status.FAILED
            order.raw_response = {
                **(order.raw_response or {}),
                "verification_error": str(exc),
            }
            order.save(update_fields=["status", "raw_response", "updated_at"])
            return Response(
                {
                    "detail": "Payment signature verification failed.",
                    "code": "payment_verification_failed",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            payment.get("order_id") != order.razorpay_order_id
            or payment.get("amount") != order.amount_inr * 100
        ):
            order.status = RazorpayOrder.Status.FAILED
            order.raw_response = {
                **(order.raw_response or {}),
                "payment": payment,
                "verification_error": "amount_or_order_mismatch",
            }
            order.save(update_fields=["status", "raw_response", "updated_at"])
            return Response(
                {
                    "detail": "Payment amount/order did not match.",
                    "code": "payment_mismatch",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        sub = activate_subscription(
            request.user,
            plan,
            provider="razorpay",
            provider_payment_id=data["razorpay_payment_id"],
            notes=f"Razorpay order {order.razorpay_order_id}",
            customer_gstin=order.customer_gstin,
        )
        order.subscription = sub
        order.status = RazorpayOrder.Status.PAID
        order.razorpay_payment_id = data["razorpay_payment_id"]
        order.raw_response = {
            **(order.raw_response or {}),
            "payment": payment,
        }
        order.save(update_fields=[
            "subscription", "status", "razorpay_payment_id",
            "raw_response", "updated_at",
        ])
        return Response(SubscriptionSerializer(sub).data, status=status.HTTP_201_CREATED)


class ActivateSubscriptionView(APIView):
    """Activate a plan for the current user.

    Demo behaviour (no payment gateway integrated yet):
      • In DEBUG / staging this immediately creates a Subscription row.
      • In production this is disabled unless the operator sets
        SUBSCRIPTION_ALLOW_DEMO_ACTIVATION=True so we don't accidentally
        give away paid plans before the gateway is wired up.
    """
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        if not _allow_demo():
            return Response(
                {
                    "detail": (
                        "Payments are not configured yet. Please come back "
                        "soon — we're getting the gateway ready."
                    ),
                    "code": "gateway_not_configured",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        ser = ActivateSubscriptionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        plan = get_plan(ser.validated_data["plan"])
        if not plan or plan.code == "free":
            return Response(
                {"detail": "Unknown or non-purchasable plan."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sub = activate_subscription(
            request.user,
            plan,
            provider="demo",
            provider_payment_id=ser.validated_data.get("provider_payment_id") or "",
            notes="Activated via /subscriptions/activate/ (demo)",
        )
        return Response(SubscriptionSerializer(sub).data, status=status.HTTP_201_CREATED)


class RazorpayWebhookView(APIView):
    """Razorpay webhook fallback for payment capture events.

    The normal browser flow uses /verify-payment/. This webhook still matters:
    if the user's browser closes after payment, Razorpay can call us directly
    and we can activate the plan by matching the order id stored locally.
    """

    permission_classes = (permissions.AllowAny,)
    authentication_classes = ()

    def post(self, request):
        secret = getattr(dj_settings, "RAZORPAY_WEBHOOK_SECRET", "")
        if not secret:
            return Response(
                {"detail": "Webhook secret is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        signature = request.headers.get("X-Razorpay-Signature", "")
        expected = hmac.new(
            secret.encode("utf-8"),
            request.body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return Response(
                {"detail": "Invalid webhook signature."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            event = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return Response(
                {"detail": "Invalid webhook payload."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        event_name = event.get("event")
        payload = event.get("payload", {})
        payment = payload.get("payment", {}).get("entity", {})
        order_payload = payload.get("order", {}).get("entity", {})
        order_id = payment.get("order_id") or order_payload.get("id")
        payment_id = payment.get("id", "")

        if event_name in {"payment.captured", "order.paid"} and order_id:
            order = (
                RazorpayOrder.objects
                .select_related("user", "subscription")
                .filter(razorpay_order_id=order_id)
                .first()
            )
            if order and order.status != RazorpayOrder.Status.PAID:
                plan = get_plan(order.plan)
                if plan and plan.code != "free":
                    sub = activate_subscription(
                        order.user,
                        plan,
                        provider="razorpay",
                        provider_payment_id=payment_id,
                        notes=f"Activated by Razorpay webhook: {event_name}",
                        customer_gstin=order.customer_gstin,
                    )
                    order.subscription = sub
                    order.status = RazorpayOrder.Status.PAID
                    order.razorpay_payment_id = payment_id
                    order.raw_response = {
                        **(order.raw_response or {}),
                        "webhook": event,
                    }
                    order.save(update_fields=[
                        "subscription", "status", "razorpay_payment_id",
                        "raw_response", "updated_at",
                    ])

        return Response({"ok": True})


def _build_invoice_payload(sub: Subscription, *, user) -> dict:
    """Single source of truth for invoice/billing payload.

    Looks up the Razorpay order linked to this subscription (if any) so the
    UI can show real `razorpay_order_id` + `razorpay_payment_id`. For demo or
    manually-activated rows the same shape is returned with empty IDs and a
    plain text receipt number derived from the subscription id.
    """
    plan = get_plan(sub.plan)
    plan_name = plan.name if plan else sub.plan

    rzp_order = getattr(sub, "razorpay_order", None)
    razorpay_order_id = rzp_order.razorpay_order_id if rzp_order else ""
    razorpay_payment_id = (
        rzp_order.razorpay_payment_id
        if rzp_order
        else sub.provider_payment_id
    )
    receipt = rzp_order.receipt if rzp_order else f"ocb_sub_{sub.id.hex[:12]}"

    # Human-friendly invoice number: OCB-YYYYMMDD-<short>
    invoice_number = (
        f"OCB-{sub.started_at:%Y%m%d}-{str(sub.id).split('-')[0].upper()}"
    )

    # Legacy rows (pre-GST) stored only amount_inr → treat it as the taxable
    # value with no GST so the invoice still totals correctly.
    base_inr = sub.base_inr or sub.amount_inr
    gst_inr = sub.gst_inr or 0

    return {
        "subscription_id": str(sub.id),
        "invoice_number": invoice_number,
        "receipt": receipt,
        "issued_at": sub.created_at,
        "plan_code": sub.plan,
        "plan_name": plan_name,
        "amount_inr": sub.amount_inr,
        "base_inr": base_inr,
        "gst_inr": gst_inr,
        "gst_rate": GST_RATE_PERCENT,
        "currency": "INR",
        "status": sub.status,
        "started_at": sub.started_at,
        "expires_at": sub.expires_at,
        "provider": sub.provider,
        "razorpay_order_id": razorpay_order_id,
        "razorpay_payment_id": razorpay_payment_id,
        "customer": {
            "name": user.name,
            "email": user.email or "",
            "phone": user.phone,
            "city": user.city or "",
            "gstin": sub.customer_gstin or "",
        },
        "seller": seller_invoice_block(),
    }


def _build_boost_invoice_payload(order, *, user) -> dict:
    """Invoice payload for one paid listing-boost order."""
    from apps.listings.boost import get_boost_package

    pkg = get_boost_package(order.package)
    invoice_number = f"OCB-BOOST-{str(order.id).split('-')[0].upper()}"
    base_inr = order.base_inr or order.amount_inr
    gst_inr = order.gst_inr or 0
    return {
        "boost_order_id": str(order.id),
        "invoice_number": invoice_number,
        "receipt": order.receipt,
        "issued_at": order.created_at,
        "package": order.package,
        "package_name": pkg.name if pkg else order.package,
        "duration_days": order.duration_days,
        "amount_inr": order.amount_inr,
        "base_inr": base_inr,
        "gst_inr": gst_inr,
        "gst_rate": GST_RATE_PERCENT,
        "currency": "INR",
        "status": order.status,
        "boosted_until": order.boosted_until,
        "provider": "razorpay",
        "razorpay_order_id": order.razorpay_order_id,
        "razorpay_payment_id": order.razorpay_payment_id,
        "listing_id": str(order.listing_id) if order.listing_id else "",
        "listing_title": order.listing.title if order.listing_id else "—",
        "customer": {
            "name": user.name,
            "email": user.email or "",
            "phone": user.phone,
            "city": user.city or "",
            "gstin": order.customer_gstin or "",
        },
        "seller": seller_invoice_block(),
    }


class MySubscriptionsView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        from apps.listings.models import ListingBoostOrder

        qs = (
            Subscription.objects
            .filter(user=request.user)
            .select_related("razorpay_order")
            .order_by("-created_at")
        )
        invoices = [_build_invoice_payload(sub, user=request.user) for sub in qs]

        boost_qs = (
            ListingBoostOrder.objects
            .filter(user=request.user, status=ListingBoostOrder.Status.PAID)
            .select_related("listing")
            .order_by("-created_at")
        )
        boost_invoices = [
            _build_boost_invoice_payload(order, user=request.user)
            for order in boost_qs
        ]

        return Response({
            "subscriptions": SubscriptionSerializer(qs, many=True).data,
            "invoices": invoices,
            "boost_invoices": boost_invoices,
        })


class SubscriptionInvoiceView(APIView):
    """Single invoice payload for `GET /subscriptions/<id>/invoice/`."""

    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request, sub_id):
        sub = (
            Subscription.objects
            .filter(user=request.user, id=sub_id)
            .select_related("razorpay_order")
            .first()
        )
        if not sub:
            return Response(
                {"detail": "Invoice not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(_build_invoice_payload(sub, user=request.user))
