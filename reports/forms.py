from django import forms
from .models import Report


# Formularz zgłoszeniowy (czterostopniowy)
class ReportCreateForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = [
            # Dane osobowe właściciela
            "owner_first_name", "owner_last_name", "owner_email", "owner_phone",
            "owner_address_street", "owner_address_postcode", "owner_address_city",
            "emergency_contact",

            # Dane pojazdu
            "vehicle_make", "vehicle_model", "production_year",
            "vehicle_color", "vehicle_type", "vehicle_plate",
            "vehicle_vin", "engine_number", "special_marks",

            # Kradzież
            "theft_datetime", "theft_place", "description",
            "witness_info", "police_report_details",

            # Multimedia i dodatkowe informacje
            "photo", "video", "suspect_description", "additional_notes", "formal_consent",
        ]

        labels = {
            "owner_first_name": "Imię właściciela",
            "owner_last_name": "Nazwisko właściciela",
            "owner_email": "Adres e-mail właściciela",
            "owner_phone": "Numer telefonu",
            "owner_address_street": "Ulica i numer domu",
            "owner_address_postcode": "Kod pocztowy",
            "owner_address_city": "Miasto",
            "emergency_contact": "Osoba do kontaktu w nagłych wypadkach",

            "vehicle_make": "Marka pojazdu",
            "vehicle_model": "Model pojazdu",
            "production_year": "Rok produkcji",
            "vehicle_color": "Kolor pojazdu",
            "vehicle_type": "Typ pojazdu",
            "vehicle_plate": "Numer rejestracyjny",
            "vehicle_vin": "Numer VIN",
            "engine_number": "Numer silnika",
            "special_marks": "Znaki szczególne pojazdu",

            "theft_datetime": "Data i godzina kradzieży",
            "theft_place": "Miejsce kradzieży",
            "description": "Okoliczności kradzieży",
            "witness_info": "Informacje o świadkach",
            "police_report_details": "Informacje o zgłoszeniu na policję",

            "photo": "Zdjęcie pojazdu (opcjonalne)",
            "video": "Nagranie wideo (opcjonalne)",
            "suspect_description": "Opis podejrzanych (jeśli dostępny)",
            "additional_notes": "Dodatkowe obserwacje",
            "formal_consent": "Potwierdzam poprawność i zgodność danych",
        }

        widgets = {
            #  Czysty datetime-local, który pozwala ręcznie ustawić datę i godzinę
            "theft_datetime": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local",
                    "class": "form-control",
                    "step": "60",  # zmiana co 1 minutę
                },
                format="%Y-%m-%dT%H:%M",
            ),
            "description": forms.Textarea(attrs={"rows": 3, "class": "form-control"}),
            "witness_info": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "police_report_details": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "special_marks": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "suspect_description": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
            "additional_notes": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
        }

    # Zostawiamy czysty konstruktor — nic nie nadpisuje pola daty
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def clean_vehicle_plate(self):
        plate = self.cleaned_data["vehicle_plate"].strip().upper()
        return plate


# Formularz sprawdzania statusu po numerze zgłoszenia
class StatusLookupForm(forms.Form):
    ticket_number = forms.CharField(
        max_length=20,
        label="Numer zgłoszenia",
        help_text="Wpisz numer otrzymany po wysłaniu formularza.",
    )


# Formularz dla policjanta - zmiana statusu
class ReportStatusForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ["status"]
        labels = {"status": "Nowy status zgłoszenia"}
