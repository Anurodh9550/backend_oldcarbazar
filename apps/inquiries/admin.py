from django.contrib import admin
from .models import Inquiry


@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = (
        "listing_title", "buyer_name", "buyer_phone",
        "channel", "status", "created_at",
    )
    list_filter = ("status", "channel", "city")
    search_fields = ("buyer_name", "buyer_phone", "listing_title", "message")
