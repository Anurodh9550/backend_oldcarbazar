from django.contrib import admin

from .models import Subscription


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
