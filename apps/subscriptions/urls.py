from django.urls import path

from .views import (
    ActivateSubscriptionView,
    MySubscriptionsView,
    PlansView,
    SubscriptionStatusView,
)

urlpatterns = [
    path("plans/", PlansView.as_view(), name="subscription-plans"),
    path("status/", SubscriptionStatusView.as_view(), name="subscription-status"),
    path("activate/", ActivateSubscriptionView.as_view(), name="subscription-activate"),
    path("mine/", MySubscriptionsView.as_view(), name="subscription-mine"),
]
