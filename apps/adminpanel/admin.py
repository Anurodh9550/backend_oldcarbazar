from django.contrib import admin
from .models import ActivityLog, Admin, AppSettings


@admin.register(Admin)
class AdminOperatorAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "role", "last_login_at")
    list_filter = ("role",)
    search_fields = ("name", "email")
    readonly_fields = ("last_login_at", "created_at")
    fields = ("name", "email", "role", "avatar_url", "password_hash",
              "last_login_at", "created_at")


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("type", "message", "target", "created_at")
    list_filter = ("type",)
    search_fields = ("message", "target")
    readonly_fields = ("created_at",)


@admin.register(AppSettings)
class AppSettingsAdmin(admin.ModelAdmin):
    list_display = ("id", "auto_approve_listings", "maintenance_mode", "updated_at")
