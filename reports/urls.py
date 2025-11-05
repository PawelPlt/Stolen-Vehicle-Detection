from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),  # Strona główna
    path("zgloszenie/", views.report_create, name="report_create"),  # Formularz zgłoszenia
    path("zgloszenie/<str:ticket_number>/sukces/", views.report_success, name="report_success"),
    path("status/", views.status_lookup, name="status_lookup"),  # Sprawdzenie statusu
    path("moje-zgloszenia/", views.my_reports, name="my_reports"),  # Moje zgłoszenia
    path("zgloszenie/<uuid:pk>/", views.ReportDetailView.as_view(), name="report_detail"),  # Szczegóły zgłoszenia
    path("zgloszenie/<uuid:pk>/edytuj/", views.report_edit, name="report_edit"),  # Edycja zgłoszenia
]

from django.conf import settings
from django.conf.urls.static import static

# Umozliwa serwerowanie pikow podczas deployumentu
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)