# filtrowanie i wyszukiwanie zgloszen
from django.contrib import admin
from .models import Report

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("ticket_number", "vehicle_plate", "status", "owner_email", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("ticket_number", "vehicle_plate", "owner_email")
    actions = ["delete_selected"]