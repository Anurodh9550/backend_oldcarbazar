from django.urls import path

from .views import (
    ActivateSubscriptionView,
    CreateRazorpayOrderView,
    MySubscriptionsView,
    PlansView,
    RazorpayWebhookView,
    SubscriptionInvoiceView,
    SubscriptionStatusView,
    VerifyRazorpayPaymentView,
)

urlpatterns = [
    path("plans/", PlansView.as_view(), name="subscription-plans"),
    path("status/", SubscriptionStatusView.as_view(), name="subscription-status"),
    path(
        "create-order/",
        CreateRazorpayOrderView.as_view(),
        name="subscription-create-order",
    ),
    path(
        "verify-payment/",
        VerifyRazorpayPaymentView.as_view(),
        name="subscription-verify-payment",
    ),
    path(
        "webhook/",
        RazorpayWebhookView.as_view(),
        name="subscription-razorpay-webhook",
    ),
    path("activate/", ActivateSubscriptionView.as_view(), name="subscription-activate"),
    path("mine/", MySubscriptionsView.as_view(), name="subscription-mine"),
    path(
        "<uuid:sub_id>/invoice/",
        SubscriptionInvoiceView.as_view(),
        name="subscription-invoice",
    ),
]
