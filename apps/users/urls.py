from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .dealers import DealerDetailView, DealersListView
from .views import (
    LoginView,
    MeView,
    OtpSendView,
    OtpVerifyView,
    RegisterView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("otp/send/", OtpSendView.as_view(), name="otp-send"),
    path("otp/verify/", OtpVerifyView.as_view(), name="otp-verify"),
]

# Public dealer directory — mounted at /api/v1/dealers/ from
# config.urls. Kept in its own list so this file stays grouped by
# concern (auth vs. directory).
dealer_urls = [
    path("", DealersListView.as_view(), name="dealer-list"),
    path("<uuid:dealer_id>/", DealerDetailView.as_view(), name="dealer-detail"),
]
