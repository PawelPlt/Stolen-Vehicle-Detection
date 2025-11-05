# dashboards/views.py
from django.shortcuts import render, get_object_or_404, redirect
from reports.models import Report
from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator
from django.contrib import messages
from reports.forms import ReportStatusForm

# Sprawdza czy użytkownik jest funkcjonariuszem
def is_officer(user):
    return user.is_authenticated and user.groups.filter(name="Funkcjonariusz").exists()

@user_passes_test(is_officer)
def officer_dashboard(request):
    filter_status = request.GET.get("status")

    reports = Report.objects.all().order_by("-created_at")
    if filter_status and filter_status != "ALL":
        reports = reports.filter(status=filter_status)

    total = Report.objects.count()
    pending = Report.objects.filter(status=Report.Status.NEW).count()
    under_analysis = Report.objects.filter(status=Report.Status.ANALYSIS).count()
    matched = Report.objects.filter(status=Report.Status.MATCHED).count()
    uncertain = Report.objects.filter(status=Report.Status.UNCERTAIN).count()
    closed = Report.objects.filter(status=Report.Status.CLOSED).count()

    # Teraz priorytetowe = dopasowane
    high_priority = Report.objects.filter(status=Report.Status.MATCHED).order_by("-created_at")[:5]

    from django.core.paginator import Paginator
    page = Paginator(reports, 10).get_page(request.GET.get("page"))

    return render(request, "dashboards/officer_dashboard.html", {
        "page": page,
        "total": total,
        "pending": pending,
        "under_analysis": under_analysis,
        "matched": matched,
        "uncertain": uncertain,
        "closed": closed,
        "high_priority": high_priority,
        "filter_status": filter_status or "ALL",
    })




@user_passes_test(is_officer)
def officer_report_detail(request, pk):
    report = get_object_or_404(Report, pk=pk)
    return render(request, "dashboards/officer_report_detail.html", {"report": report})


@user_passes_test(is_officer)
def officer_report_status_update(request, pk):
    report = get_object_or_404(Report, pk=pk)
    if request.method == "POST":
        form = ReportStatusForm(request.POST, instance=report)
        if form.is_valid():
            form.save()
            messages.success(request, "Zmieniono status zgłoszenia.")
            return redirect("officer_dashboard")
    else:
        form = ReportStatusForm(instance=report)
    return render(request, "dashboards/officer_report_status_update.html", {"form": form, "report": report})


# 📄 Generowanie raportu PDF
from django.http import HttpResponse, Http404
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas






@user_passes_test(is_officer)
def report_pdf(request, pk):
    """Generuje raport PDF ze wszystkimi danymi zgłoszenia (bez załączników)."""
    try:
        report = Report.objects.get(pk=pk)
    except Report.DoesNotExist:
        raise Http404("Zgłoszenie nie istnieje")

    # 📄 Przygotowanie pliku PDF
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="Raport_{report.ticket_number}.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    y = height - 2 * cm

    # 🔹 Nagłówek dokumentu
    p.setFont("Helvetica-Bold", 16)
    p.drawString(2 * cm, y, f"Raport zgłoszenia {report.ticket_number}")
    y -= 0.8 * cm
    p.setFont("Helvetica", 11)
    p.drawString(2 * cm, y, f"Status: {report.get_status_display()}")
    y -= 1.2 * cm

    # 🔹 Sekcja 1 — Dane właściciela
    p.setFont("Helvetica-Bold", 13)
    p.drawString(2 * cm, y, "Dane właściciela:")
    y -= 0.7 * cm
    p.setFont("Helvetica", 10)
    lines = [
        f"Imię: {report.owner_first_name}",
        f"Nazwisko: {report.owner_last_name}",
        f"E-mail: {report.owner_email}",
        f"Telefon: {report.owner_phone or '-'}",
        f"Adres: {report.owner_address_street}, {report.owner_address_postcode} {report.owner_address_city}",
        f"Kontakt awaryjny: {report.emergency_contact or '-'}",
    ]
    for line in lines:
        p.drawString(2.5 * cm, y, line)
        y -= 0.45 * cm

    y -= 0.5 * cm

    # 🔹 Sekcja 2 — Dane pojazdu
    p.setFont("Helvetica-Bold", 13)
    p.drawString(2 * cm, y, "Dane pojazdu:")
    y -= 0.7 * cm
    p.setFont("Helvetica", 10)
    lines = [
        f"Marka: {report.vehicle_make}",
        f"Model: {report.vehicle_model}",
        f"Rok produkcji: {report.production_year}",
        f"Kolor: {report.vehicle_color}",
        f"Typ: {report.vehicle_type}",
        f"Numer rejestracyjny: {report.vehicle_plate}",
        f"Numer VIN: {report.vehicle_vin}",
        f"Numer silnika: {report.engine_number}",
        f"Znaki szczególne: {report.special_marks or '-'}",
    ]
    for line in lines:
        p.drawString(2.5 * cm, y, line)
        y -= 0.45 * cm

    y -= 0.5 * cm

    # 🔹 Sekcja 3 — Szczegóły kradzieży
    p.setFont("Helvetica-Bold", 13)
    p.drawString(2 * cm, y, "Szczegóły kradzieży:")
    y -= 0.7 * cm
    p.setFont("Helvetica", 10)
    lines = [
        f"Data i godzina: {report.theft_datetime.strftime('%Y-%m-%d %H:%M')}",
        f"Miejsce: {report.theft_place}",
        f"Opis: {report.description or '-'}",
        f"Świadkowie: {report.witness_info or '-'}",
        f"Zgłoszenie na policję: {report.police_report_details or '-'}",
    ]
    for line in lines:
        p.drawString(2.5 * cm, y, line)
        y -= 0.45 * cm

    y -= 0.5 * cm

    # 🔹 Sekcja 4 — Dodatkowe informacje
    p.setFont("Helvetica-Bold", 13)
    p.drawString(2 * cm, y, "Dodatkowe informacje:")
    y -= 0.7 * cm
    p.setFont("Helvetica", 10)
    lines = [
        f"Opis podejrzanych: {report.suspect_description or '-'}",
        f"Dodatkowe obserwacje: {report.additional_notes or '-'}",
    ]
    for line in lines:
        p.drawString(2.5 * cm, y, line)
        y -= 0.45 * cm

    # 🔹 Stopka
    p.setFont("Helvetica-Oblique", 9)
    p.drawString(2 * cm, 1.5 * cm, "© 2025 SkradzionePojazdy – Projekt inżynierski, Python Django")

    # Zakończenie
    p.showPage()
    p.save()
    return response
