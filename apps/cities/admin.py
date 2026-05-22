from django.contrib import admin
from .models import City


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "state", "popular", "car_count")
    list_filter = ("popular", "state")
    search_fields = ("name", "state")
