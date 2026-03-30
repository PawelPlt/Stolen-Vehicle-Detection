from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.hashers import check_password

User = get_user_model()

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label="Adres e-mail",
        widget=forms.EmailInput(attrs={"class": "form-control"})
    )

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Ten adres e-mail jest już używany.")
        return email


class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(label="Imię", required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    last_name = forms.CharField(label="Nazwisko", required=False, widget=forms.TextInput(attrs={"class": "form-control"}))
    email = forms.EmailField(label="E-mail", required=True, widget=forms.EmailInput(attrs={"class": "form-control"}))

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        qs = User.objects.filter(email=email)
        if self.user:
            qs = qs.exclude(pk=self.user.pk)
        if qs.exists():
            raise forms.ValidationError("Ten adres e-mail jest już używany.")
        return email


class DeleteAccountForm(forms.Form):
    password = forms.CharField(
        label="Potwierdź hasło",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def clean_password(self):
        pwd = self.cleaned_data["password"]
        if not self.user or not self.user.check_password(pwd):
            raise forms.ValidationError("Nieprawidłowe hasło.")
        return pwd
