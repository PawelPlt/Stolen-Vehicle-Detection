from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),  # dodaje ścieżki z acounts/urls
    #path("accounts/", include("django.contrib.auth.urls")),   # login, logout, reset hasła
    path("", include("reports.urls")),   # dodaje sciezki z reports/urls
    path("funkcjonariusz/", include("dashboards.urls")),

]

# Pozwala serwować pliki podczas developmentu
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
