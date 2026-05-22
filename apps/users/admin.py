from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import OtpCode, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ("-date_joined",)
    list_display = ("name", "phone", "email", "role", "status", "date_joined")
    list_filter = ("role", "status", "is_staff")
    search_fields = ("name", "email", "phone", "city")
    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        ("Profile", {"fields": ("name", "email", "city", "avatar_url")}),
        ("Role", {"fields": ("role", "status", "email_verified", "phone_verified")}),
        ("Admin", {"fields": ("admin_note", "is_staff", "is_superuser", "groups")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("name", "phone", "email", "password1", "password2", "role"),
        }),
    )


@admin.register(OtpCode)
class OtpAdmin(admin.ModelAdmin):
    list_display = ("target", "purpose", "code", "created_at", "expires_at", "consumed_at")
    list_filter = ("purpose",)
    search_fields = ("target",)
