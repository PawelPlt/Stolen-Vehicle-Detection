from django.urls import path
from . import views

urlpatterns = [
    path("", views.officer_dashboard, name="officer_dashboard"),
    path("<uuid:pk>/", views.officer_report_detail, name="officer_report_detail"),
    path("<uuid:pk>/status/", views.officer_report_status_update, name="officer_report_status_update"),
    path("<uuid:pk>/pdf/", views.report_pdf, name="report_pdf"),
]

