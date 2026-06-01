"""Subscription API.

Endpoints (all under `/api/v1/subscriptions/`):

    GET  /plans/      Public list of plan options (free + paid).
    GET  /status/     Auth required. Current user's plan + quota usage.
    POST /activate/   Auth required. Demo activation — to be replaced
                      by a real payment-gateway webhook later.
    GET  /mine/       Auth required. History of this user's paid rows.
"""
from django.conf import settings as dj_settings
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Subscription
from .plans import ALL_PLANS, get_plan
from .serializers import (
    ActivateSubscriptionSerializer,
    PlanSerializer,
    SubscriptionSerializer,
    SubscriptionStatusSerializer,
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


class MySubscriptionsView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        qs = Subscription.objects.filter(user=request.user).order_by("-created_at")
        return Response(
            {"subscriptions": SubscriptionSerializer(qs, many=True).data}
        )
