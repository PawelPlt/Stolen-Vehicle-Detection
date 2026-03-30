from django.contrib import admin
from .models import Report, Evidence

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("ticket_number", "vehicle_plate", "status", "owner_email", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("ticket_number", "vehicle_plate", "owner_email")
    actions = ["delete_selected"]

@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "matched_report", "match_confidence", "created_by", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("id", "detected_plates_json")
    readonly_fields = ("detected_plates_json", "matched_report", "match_confidence", "status", "created_at")

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    actions = ["reprocess_selected"]

    def reprocess_selected(self, request, queryset):
        for ev in queryset:
            # wyczyść wyniki i ponownie zapisz -> uruchomi OCR + dopasowanie
            ev.detected_plates_json = ""
            ev.matched_report = None
            ev.match_confidence = 0.0
            ev.status = ev.Status.PENDING
            ev.save()
        self.message_user(request, f"Ponownie przeanalizowano {queryset.count()} pozycji.")
    reprocess_selected.short_description = "Ponownie przeanalizuj wybrane"
