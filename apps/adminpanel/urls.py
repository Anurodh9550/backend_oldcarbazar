from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.users.views import UserAdminViewSet
from .views import (
    ActivityLogViewSet,
    AdminLoginView,
    AdminMeView,
    AdminPaymentsView,
    AppSettingsView,
    DashboardStatsView,
    DealerOfferRevokeView,
    DealerOffersView,
)

router = DefaultRouter()
router.register("users", UserAdminViewSet, basename="admin-users")
router.register("activity", ActivityLogViewSet, basename="admin-activity")

urlpatterns = [
    path("login/", AdminLoginView.as_view(), name="admin-login"),
    path("me/", AdminMeView.as_view(), name="admin-me"),
    path("dashboard/", DashboardStatsView.as_view(), name="admin-dashboard"),
    path("payments/", AdminPaymentsView.as_view(), name="admin-payments"),
    path("dealer-offers/", DealerOffersView.as_view(), name="admin-dealer-offers"),
    path(
        "dealer-offers/<uuid:sub_id>/revoke/",
        DealerOfferRevokeView.as_view(),
        name="admin-dealer-offer-revoke",
    ),
    path("settings/", AppSettingsView.as_view(), name="admin-settings"),
    *router.urls,
]
