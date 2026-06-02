from django.contrib import admin

from .models import RazorpayOrder, Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "user", "plan", "status", "amount_inr",
        "started_at", "expires_at", "provider",
    )
    list_filter = ("plan", "status", "provider")
    search_fields = (
        "user__name", "user__email", "user__phone",
        "provider_payment_id",
    )
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)


@admin.register(RazorpayOrder)
class RazorpayOrderAdmin(admin.ModelAdmin):
    list_display = (
        "razorpay_order_id", "user", "plan", "amount_inr",
        "status", "razorpay_payment_id", "created_at",
    )
    list_filter = ("plan", "status")
    search_fields = (
        "razorpay_order_id", "razorpay_payment_id",
        "receipt", "user__name", "user__phone", "user__email",
    )
    readonly_fields = (
        "id", "raw_response", "created_at", "updated_at",
    )
    ordering = ("-created_at",)
