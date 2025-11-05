from django.db import models
from django.contrib.auth import get_user_model
import uuid
import time
from difflib import SequenceMatcher
from django.core.mail import send_mail
from django.conf import settings
import os

# 🧠 Moduł OCR
from ai.ocr import extract_license_plate, extract_from_video

User = get_user_model()


class Report(models.Model):
    """Model przechowujący zgłoszenia o skradzionych pojazdach."""

    class Status(models.TextChoices):
        NEW = "NEW", "Oczekujące"
        ANALYSIS = "ANALYSIS", "W trakcie analizy"
        MATCHED = "MATCHED", "Dopasowano"
        UNCERTAIN = "UNCERTAIN", "Niepewne"
        UNMATCHED = "UNMATCHED", "Brak dopasowania"
        CLOSED = "CLOSED", "Zamknięte"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket_number = models.CharField(max_length=20, unique=True, editable=False)

    # 👤 Dane właściciela
    owner_first_name = models.CharField(max_length=50)
    owner_last_name = models.CharField(max_length=80)
    owner_email = models.EmailField()
    owner_phone = models.CharField(max_length=32, blank=True)
    owner_address_street = models.CharField(max_length=100, blank=True)
    owner_address_city = models.CharField(max_length=50, blank=True)
    owner_address_postcode = models.CharField(max_length=10, blank=True)
    emergency_contact = models.CharField(max_length=100, blank=True)

    # 🚗 Dane pojazdu
    vehicle_make = models.CharField(max_length=50, blank=True)
    vehicle_model = models.CharField(max_length=50, blank=True)
    production_year = models.PositiveIntegerField(blank=True, null=True)
    vehicle_color = models.CharField(max_length=30, blank=True)
    vehicle_type = models.CharField(max_length=50, blank=True)
    vehicle_plate = models.CharField(max_length=16)
    vehicle_vin = models.CharField(max_length=50, blank=True)
    engine_number = models.CharField(max_length=50, blank=True)
    special_marks = models.TextField(blank=True)

    # 📅 Okoliczności kradzieży
    theft_datetime = models.DateTimeField()
    theft_place = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    witness_info = models.TextField(blank=True)
    police_report_details = models.TextField(blank=True)

    # 📷 Pliki
    photo = models.ImageField(upload_to="reports_photos/", blank=True, null=True)
    video = models.FileField(upload_to="reports_videos/", blank=True, null=True)

    # 🧾 Dodatkowe informacje
    suspect_description = models.TextField(blank=True)
    additional_notes = models.TextField(blank=True)
    formal_consent = models.BooleanField(default=False)

    # 🧠 Wykryta przez AI tablica
    vehicle_plate_detected = models.CharField(max_length=16, blank=True, null=True)

    # ⚙️ Status i metadane
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.NEW)
    created_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="reports"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def delete_old_files(self):
        """Usuwa stare pliki zdjęć/wideo z dysku, jeśli nie są już powiązane z obiektem."""
        for field in ["photo", "video"]:
            file_field = getattr(self, field)
            if file_field and os.path.isfile(file_field.path):
                try:
                    os.remove(file_field.path)
                    print(f"[CLEANUP] Usunięto plik: {file_field.path}")
                except Exception as e:
                    print(f"[CLEANUP ERROR] Nie udało się usunąć {file_field.path}: {e}")

    def normalize_plate(self, plate: str):
        """Usuwa spacje, myślniki i zmienia litery na wielkie."""
        return plate.replace(" ", "").replace("-", "").upper() if plate else ""

    def delete(self, *args, **kwargs):
        """Usuwa powiązane pliki z dysku przy kasowaniu raportu."""
        self.delete_old_files()
        super().delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        """Nadpisana metoda save() — analizuje plik i ustala status zgodności tablic."""
        is_new = self._state.adding
        old_photo, old_video, old_status = None, None, None

        if not is_new:
            old = Report.objects.filter(pk=self.pk).first()
            if old:
                old_photo = old.photo
                old_video = old.video
                old_status = old.status

        # 🧹 Usuwanie starego pliku, jeśli admin kliknął "Clear"
        if not self.photo and old_photo:
            if old_photo and os.path.isfile(old_photo.path):
                try:
                    os.remove(old_photo.path)
                    print(f"[CLEANUP] Usunięto stare zdjęcie: {old_photo.path}")
                except Exception as e:
                    print(f"[CLEANUP ERROR] {e}")

        if not self.video and old_video:
            if old_video and os.path.isfile(old_video.path):
                try:
                    os.remove(old_video.path)
                    print(f"[CLEANUP] Usunięto stary film: {old_video.path}")
                except Exception as e:
                    print(f"[CLEANUP ERROR] {e}")

        # 🆕 Numer zgłoszenia
        if not self.ticket_number:
            base = str(uuid.uuid4())[:6].upper()
            self.ticket_number = f"SC-{base}"

        super().save(*args, **kwargs)

        # 🔄 Analiza tylko przy nowym pliku
        if is_new or (self.photo and self.photo != old_photo) or (self.video and self.video != old_video):
            print("[AI] Uruchamianie analizy OCR...")
            start = time.time()

            self.status = Report.Status.ANALYSIS
            super().save(update_fields=["status"])

            try:
                detected_plate = None
                detected_plates = []

                # 🧠 Analiza zdjęcia lub filmu
                if self.photo:
                    detected_plate = extract_license_plate(self.photo.path)
                elif self.video:
                    detected_plates = extract_from_video(self.video.path) or []

                similarity = 0.0

                # 🎥 Jeśli film — sprawdź wszystkie wykryte tablice
                if detected_plates:
                    best_match = None
                    best_ratio = 0.0
                    for plate in detected_plates:
                        p1 = self.normalize_plate(self.vehicle_plate)
                        p2 = self.normalize_plate(plate)
                        ratio = SequenceMatcher(None, p1, p2).ratio()
                        print(f"[AI] 🔍 Porównanie {p1} ↔ {p2} → {ratio*100:.1f}%")
                        if ratio > best_ratio:
                            best_ratio = ratio
                            best_match = plate

                    detected_plate = best_match
                    similarity = best_ratio * 100
                    print(f"[AI] 📊 Najlepsze dopasowanie: {detected_plate} ({similarity:.1f}%)")

                # 🖼️ Jeśli zdjęcie — standardowa analiza
                elif detected_plate:
                    p1 = self.normalize_plate(self.vehicle_plate)
                    p2 = self.normalize_plate(detected_plate)
                    ratio = SequenceMatcher(None, p1, p2).ratio()
                    similarity = ratio * 100
                    print(f"[AI] 📊 Zgodność OCR z tablicą właściciela: {similarity:.1f}%")

                if detected_plate:
                    self.vehicle_plate_detected = detected_plate

                    if similarity == 100:
                        self.status = Report.Status.MATCHED
                        print("[AI] ✅ Pełne dopasowanie tablicy.")
                    elif similarity >= 70:
                        self.status = Report.Status.UNCERTAIN
                        print("[AI] ⚠️ Tablica podobna, ale nie w 100%.")
                    else:
                        self.status = Report.Status.UNMATCHED
                        print("[AI] ❌ Tablica różni się zbyt mocno, ale zapisano wykryty numer.")
                else:
                    print("[AI] OCR nie rozpoznał żadnej tablicy.")
                    self.status = Report.Status.UNMATCHED

                # 💾 Zapisanie wykrytego numeru i statusu
                super().save(update_fields=["vehicle_plate_detected", "status"])

                duration = (time.time() - start) * 1000
                print(f"[AI] Analiza zakończona w {duration:.0f} ms")

            except Exception as e:
                print(f"[AI ERROR] {e}")
                self.status = Report.Status.UNMATCHED
                super().save(update_fields=["status"])

        # ✉️ Wysyłanie maila przy nowym zgłoszeniu lub zmianie statusu
        if is_new:
            subject = f"Potwierdzenie zgłoszenia {self.ticket_number}"
            message = (
                f"Dziękujemy za zgłoszenie!\n\n"
                f"Numer zgłoszenia: {self.ticket_number}\n"
                f"Aktualny status: {self.get_status_display()}\n\n"
                f"{settings.SITE_URL}/status/"
            )
        elif old_status and old_status != self.status:
            subject = f"Zmiana statusu zgłoszenia {self.ticket_number}"
            message = (
                f"Twój numer zgłoszenia: {self.ticket_number}\n"
                f"Nowy status: {self.get_status_display()}\n\n"
                f"Zespół SkradzionePojazdy"
            )
        else:
            subject = None
            message = None

        if subject:
            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[self.owner_email],
                    fail_silently=False,
                )
                print(f"[MAIL] Wysłano powiadomienie: {subject}")
            except Exception as e:
                print(f"[MAIL ERROR] {e}")

    def __str__(self):
        return f"{self.ticket_number} ({self.vehicle_plate})"
