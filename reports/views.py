from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse # Dwa pierwsze potrzebne do renderowania strony
from .forms import ReportCreateForm, StatusLookupForm
from .models import Report, Evidence
from django.http import HttpResponseForbidden
from django.contrib import messages
from .forms import ReportStatusForm
from .utils import officer_required
from django.contrib.auth.decorators import user_passes_test


def home(request): # Wyświetla strone home
    return render(request, "reports/home.html")

def report_create(request): # Widok nowego zgłoszenia
    if request.method == "POST": # Sprawdzam czy użytkownik kliknął "wyślij"
        form = ReportCreateForm(request.POST, request.FILES)  # POST = dane, FILES = foto/wideo
        if form.is_valid():  # Sprawdzam czy dane w formularzu są poprawne
            report = form.save(commit=False)      # jeszcze nie zapisuj, bo chcemy dopisać autora
            if request.user.is_authenticated:
                report.created_by = request.user  # zapisz „właściciela” zgłoszenia, jeśli zalogowany
            report.save()                         # teraz zapis do bazy -> wygeneruje ticket_number
            return redirect(reverse("report_success", kwargs={"ticket_number": report.ticket_number}))
    else: # Jeżeli użytkownik otworzył dopiero stronę
        form = ReportCreateForm() # Wyświetl mu pusty formularz do wypełnienia
    return render(request, "reports/report_create.html", {"form": form}) # ten "form" podaje potem w htmlu

def report_success(request, ticket_number): # Do przekierowania użytkownika
    return render(request, "reports/report_success.html", {"ticket_number": ticket_number}) # Renderuje szablon z dnymi

def status_lookup(request):
    if request.method == "POST": # Czy użytkownik kliknął "sprawdż" POST - dane wewnatrz. Jeżeli dopiero wszedł to będzie "GET"
        form = StatusLookupForm(request.POST) # Wkładamy dane
        if form.is_valid(): # Sprawdzam poprawność danych
            ticket = form.cleaned_data["ticket_number"].strip() # Pobieramy dane i usuwamy spacje
            report = get_object_or_404(Report, ticket_number=ticket) # Jeżeli znajdzie dane to zapisze do Report jezeli nie to wyrzuci 404
            return render(request, "reports/status_result.html", {"report": report})
    else:
        form = StatusLookupForm() # Jeżeli dopiero wszedłem na stronę to stworzy mi ten formularz pusty
    return render(request, "reports/status_lookup.html", {"form": form})

# Panel użytkownika - moje zgłoszenia
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator

@login_required
def my_reports(request):
    qs = (Report.objects
          .filter(created_by=request.user)
          .order_by("-created_at"))
    page = Paginator(qs, 10).get_page(request.GET.get("page"))
    return render(request, "reports/my_reports.html", {"page": page})

# Detal zgłoszenia
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView

class ReportDetailView(DetailView):
    model = Report
    template_name = "reports/report_detail.html"
    context_object_name = "report"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        report = self.get_object()
        evidences = Evidence.objects.filter(matched_report=report).order_by("-created_at")
        context["evidences"] = evidences
        return context

# Edycja zgłoszenia tylko gdy status = NEW


def is_officer(user):
    return user.is_authenticated and user.groups.filter(name="Funkcjonariusz").exists()


@login_required
def report_edit(request, pk):
    report = get_object_or_404(Report, pk=pk)

    # tylko właściciel lub funkcjonariusz
    if not (is_officer(request.user) or report.created_by_id == request.user.id):
        return HttpResponseForbidden("Brak uprawnień do edycji tego zgłoszenia.")

    # właściciel może edytować tylko gdy NEW; funkcjonariusz zawsze
    if not is_officer(request.user) and report.status != Report.Status.NEW:
        messages.error(request, "Tego zgłoszenia nie można już edytować (status nie pozwala na zmiany).")
        return redirect("report_detail", pk=report.pk)

    if request.method == "POST":
        form = ReportCreateForm(request.POST, request.FILES, instance=report)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Zapisano zmiany w zgłoszeniu.")
            return redirect("report_detail", pk=report.pk)
        else:
            messages.error(request, "⚠️ Formularz zawiera błędy. Popraw dane.")
    else:
        form = ReportCreateForm(instance=report)

    return render(request, "reports/report_edit.html", {"form": form, "report": report})



def report_detail(request, pk):
    report = get_object_or_404(Report, pk=pk)
    evidences = Evidence.objects.filter(matched_report=report)
    print("USER VIEW:", report.ticket_number, "=> znaleziono", evidences.count(), "dopasowań")
    for e in evidences:
        print("  -", e.id, e.video, e.photo, e.get_status_display())
    return render(request, "reports/report_detail.html", {"report": report, "evidences": evidences})