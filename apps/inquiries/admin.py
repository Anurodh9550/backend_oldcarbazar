from django.contrib import admin
from .models import Inquiry, Offer, TestDriveBooking


@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = (
        "listing_title", "buyer_name", "buyer_phone",
        "channel", "status", "created_at",
    )
    list_filter = ("status", "channel", "city")
    search_fields = ("buyer_name", "buyer_phone", "listing_title", "message")


@admin.register(TestDriveBooking)
class TestDriveBookingAdmin(admin.ModelAdmin):
    list_display = (
        "listing_title", "buyer_name", "buyer_phone",
        "scheduled_at", "status", "created_at",
    )
    list_filter = ("status",)
    search_fields = ("buyer_name", "buyer_phone", "listing_title")


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = (
        "listing_title", "buyer_name", "buyer_phone",
        "amount", "status", "created_at",
    )
    list_filter = ("status",)
    search_fields = ("buyer_name", "buyer_phone", "listing_title")
