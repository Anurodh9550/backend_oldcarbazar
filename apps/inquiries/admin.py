from django.contrib import admin
from .models import Inquiry, LoanInquiry, Offer, TestDriveBooking


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


@admin.register(LoanInquiry)
class LoanInquiryAdmin(admin.ModelAdmin):
    list_display = (
        "full_name", "mobile", "bank_name", "loan_partner",
        "city", "monthly_income", "status", "created_at",
    )
    list_filter = ("status", "bank_name", "loan_partner", "employment_type")
    search_fields = ("full_name", "mobile", "email", "city")
    list_editable = ("status",)
    date_hierarchy = "created_at"


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = (
        "listing_title", "buyer_name", "buyer_phone",
        "amount", "status", "created_at",
    )
    list_filter = ("status",)
    search_fields = ("buyer_name", "buyer_phone", "listing_title")
