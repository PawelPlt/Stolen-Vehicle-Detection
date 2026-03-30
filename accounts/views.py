from django.contrib import messages
from django.contrib.auth import get_user_model, logout, login as auth_login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from .forms import UserRegisterForm, UserProfileForm, DeleteAccountForm

User = get_user_model()


# Własny login z przekierowaniami po roli
class CustomLoginView(LoginView):
    template_name = "registration/login.html"
    form_class = AuthenticationForm

    def form_valid(self, form):
        user = form.get_user()
        auth_login(self.request, user)

        # 1. Administrator → panel admina
        if user.is_superuser:
            return redirect("/admin/")

        #2. Funkcjonariusz → panel funkcjonariusza
        elif user.groups.filter(name="Funkcjonariusz").exists():
            return redirect("officer_dashboard")

        # 3. Zwykły użytkownik → strona główna
        else:
            return redirect("/")


def register(request):
    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Konto utworzone. Możesz się zalogować.")
            return redirect("login")
    else:
        form = UserRegisterForm()
    return render(request, "registration/register.html", {"form": form})


@login_required
def profile(request):
    if request.method == "POST":
        form = UserProfileForm(request.POST, instance=request.user, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Dane konta zostały zaktualizowane.")
            return redirect("accounts_profile")
    else:
        form = UserProfileForm(instance=request.user, user=request.user)
    delete_form = DeleteAccountForm(user=request.user)
    return render(request, "accounts/profile.html", {"form": form, "delete_form": delete_form})


class ProfilePasswordChangeView(PasswordChangeView):
    template_name = "registration/password_change_form.html"
    success_url = reverse_lazy("password_change_done")


@login_required
def delete_account(request):
    if request.method == "POST":
        form = DeleteAccountForm(request.POST, user=request.user)
        if form.is_valid():
            user = request.user
            logout(request)
            user.delete()
            messages.success(request, "Twoje konto zostało usunięte.")
            return redirect("/")
        else:
            profile_form = UserProfileForm(instance=request.user, user=request.user)
            return render(request, "accounts/profile.html", {"form": profile_form, "delete_form": form})
    return redirect("accounts_profile")
