from django.urls import path
from django.contrib.auth import views as auth_views
from .views import CustomLoginView, register, profile, ProfilePasswordChangeView, delete_account

urlpatterns = [
    # 🔹 Nasz własny login (z przekierowaniami)
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # 🔹 Rejestracja
    path("register/", register, name="register"),

    # 🔹 Profil, zmiana hasła, usunięcie konta
    path("profile/", profile, name="accounts_profile"),
    path("password-change/", ProfilePasswordChangeView.as_view(), name="password_change"),
    path("password-change/done/", auth_views.PasswordChangeDoneView.as_view(
        template_name="registration/password_change_done.html"
    ), name="password_change_done"),

    path("delete/", delete_account, name="accounts_delete"),

    # 🔹 Resetowanie hasła (odzyskiwanie konta)
    path("password_reset/", auth_views.PasswordResetView.as_view(
        template_name="registration/password_reset_form.html"
    ), name="password_reset"),

    path("password_reset/done/", auth_views.PasswordResetDoneView.as_view(
        template_name="registration/password_reset_done.html"
    ), name="password_reset_done"),

    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="registration/password_reset_confirm.html"
    ), name="password_reset_confirm"),

    path("reset/done/", auth_views.PasswordResetCompleteView.as_view(
        template_name="registration/password_reset_complete.html"
    ), name="password_reset_complete"),
]
