from django.contrib import admin
from .models import Listing, ListingPhoto


class PhotoInline(admin.TabularInline):
    model = ListingPhoto
    extra = 0


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = (
        "title", "brand", "year", "location",
        "price_label", "moderation", "featured", "created_at",
    )
    list_filter = ("moderation", "status", "featured", "brand", "fuel", "transmission")
    search_fields = ("title", "brand", "model", "seller_phone", "location")
    inlines = [PhotoInline]
    readonly_fields = ("views", "inquiries_count", "created_at", "updated_at")


@admin.register(ListingPhoto)
class ListingPhotoAdmin(admin.ModelAdmin):
    list_display = ("listing", "position", "is_cover")
