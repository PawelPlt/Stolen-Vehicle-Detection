from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login

#Do sprawdzania uzytkownika
from django.contrib.auth import login as auth_login
from django.contrib.auth.forms import AuthenticationForm
from django.views.generic import FormView

from django.contrib import messages
from .forms import UserRegisterForm

def register(request):
    if request.method == "POST":
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Konto zostało utworzone! Możesz się teraz zalogować.")
            return redirect("login")
    else:
        form = UserRegisterForm()
    return render(request, "accounts/register.html", {"form": form})



class CustomLoginView(FormView):
    template_name = "registration/login.html"
    form_class = AuthenticationForm

    def form_valid(self, form):
        user = form.get_user()
        auth_login(self.request, user)

        # 🔹 1. Administrator → panel admina
        if user.is_superuser:
            return redirect("/admin/")

        # 🔹 2. Funkcjonariusz → panel funkcjonariusza
        elif user.groups.filter(name="Funkcjonariusz").exists():
            return redirect("officer_dashboard")

        # 🔹 3. Zwykły użytkownik → strona główna
        else:
            return redirect("/")
