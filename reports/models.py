import os
import sys
import time
import json
import uuid
from difflib import SequenceMatcher
from typing import Optional, Tuple

from django.db import models
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings

# 🧠 OCR (tylko dla Evidence)
from ai.ocr import extract_license_plate, extract_from_video

User = get_user_model()


class Report(models.Model):
    class Meta:
        verbose_name = "Zgłoszenie"
        verbose_name_plural = "Zgłoszenia"
    class Status(models.TextChoices):
        NEW = "NEW", "Oczekujące"
        ANALYSIS = "ANALYSIS", "W trakcie analizy"
        MATCHED = "MATCHED", "Dopasowano"
        UNCERTAIN = "UNCERTAIN", "Niepewne"
        UNMATCHED = "UNMATCHED", "Brak dopasowania"
        CLOSED = "CLOSED", "Zamknięte"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket_number = models.CharField(max_length=20, unique=True, editable=False)

    # Dane właściciela
    owner_first_name = models.CharField(max_length=50)
    owner_last_name = models.CharField(max_length=80)
    owner_email = models.EmailField()
    owner_phone = models.CharField(max_length=32, blank=True)
    owner_address_street = models.CharField(max_length=100, blank=True)
    owner_address_city = models.CharField(max_length=50, blank=True)
    owner_address_postcode = models.CharField(max_length=10, blank=True)
    emergency_contact = models.CharField(max_length=100, blank=True)

    # Dane pojazdu
    vehicle_make = models.CharField(max_length=50, blank=True)
    vehicle_model = models.CharField(max_length=50, blank=True)
    production_year = models.PositiveIntegerField(blank=True, null=True)
    vehicle_color = models.CharField(max_length=30, blank=True)
    vehicle_type = models.CharField(max_length=50, blank=True)
    vehicle_plate = models.CharField(max_length=16)
    vehicle_vin = models.CharField(max_length=50, blank=True)
    engine_number = models.CharField(max_length=50, blank=True)
    special_marks = models.TextField(blank=True)

    # Okoliczności kradzieży
    theft_datetime = models.DateTimeField()
    theft_place = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    witness_info = models.TextField(blank=True)
    police_report_details = models.TextField(blank=True)

    # Pliki
    photo = models.ImageField(upload_to="reports_photos/", blank=True, null=True)
    video = models.FileField(upload_to="reports_videos/", blank=True, null=True)

    # Dodatkowe informacje
    suspect_description = models.TextField(blank=True)
    additional_notes = models.TextField(blank=True)
    formal_consent = models.BooleanField(default=False)

    # Wykryta tablica
    vehicle_plate_detected = models.CharField(max_length=16, blank=True, null=True)

    # Status i metadane
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.NEW)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="reports")
    created_at = models.DateTimeField(auto_now_add=True)

    def delete_old_files(self):
        """Usuwa pliki photo/video z dysku, gdy raport jest usuwany."""
        for field in ["photo", "video"]:
            file_field = getattr(self, field)
            if file_field and file_field.name and os.path.isfile(file_field.path):
                try:
                    os.remove(file_field.path)
                    print(f"[CLEANUP] Usunięto plik: {file_field.path}")
                except Exception as e:
                    print(f"[CLEANUP ERROR] {e}")

    def delete(self, *args, **kwargs):
        self.delete_old_files()
        super().delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        is_new = self._state.adding

        if not self.ticket_number:
            base = str(uuid.uuid4())[:6].upper()
            self.ticket_number = f"SC-{base}"

        old_status = None
        if not is_new:
            old_status = Report.objects.filter(pk=self.pk).values_list("status", flat=True).first()

        super().save(*args, **kwargs)

        subject = None
        message = None
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

        if subject:
            try:
                send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [self.owner_email])
                print(f"[MAIL] Wysłano powiadomienie: {subject}")
            except Exception as e:
                print(f"[MAIL ERROR] {e}")

    def __str__(self):
        return f"{self.ticket_number} ({self.vehicle_plate})"


class Evidence(models.Model):
    class Meta:
        verbose_name = "Dowód"
        verbose_name_plural = "Dowody"
    class Status(models.TextChoices):
        PENDING = "PENDING", "W kolejce"
        MATCHED = "MATCHED", "Dopasowano"
        UNCERTAIN = "UNCERTAIN", "Niepewne"
        UNMATCHED = "UNMATCHED", "Brak dopasowania"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    photo = models.ImageField(upload_to="evidence/photos/", blank=True, null=True)
    video = models.FileField(upload_to="evidence/videos/", blank=True, null=True)
    detected_plates_json = models.TextField(blank=True)
    matched_report = models.ForeignKey("Report", null=True, blank=True, on_delete=models.SET_NULL, related_name="evidences")
    match_confidence = models.FloatField(default=0.0)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="evidences")
    created_at = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def _normalize(plate: str) -> str:
        return plate.replace(" ", "").replace("-", "").upper() if plate else ""

    def _run_ocr(self) -> list[str]:
        start = time.time()
        detected = []
        try:
            if self.photo and self.photo.name:
                print("[OCR] Analiza zdjęcia...")
                result = extract_license_plate(self.photo.path)
                if result:
                    print(f"[OCR] Wykryto tablicę: {result}")
                    detected.append(result)
                else:
                    print("[OCR] YOLO nie wykrył tablicy.")
            elif self.video and self.video.name:
                print("[OCR] Analiza wideo...")
                detected = extract_from_video(self.video.path) or []
                for idx, plate in enumerate(detected):
                    print(f"[OCR] {idx * 0.5:.2f}s → Wykryto tablicę: {plate}")
        except Exception as e:
            print(f"[EVIDENCE OCR ERROR] {e}")

        if detected:
            print("\n[OCR] Wykryte tablice:")
            for p in detected:
                print(f"   • {p}")
            print(f"\n[OCR] Łącznie różnych tablic: {len(set(detected))}")
        else:
            print("[OCR] Nie wykryto żadnych tablic.")

        end = time.time()
        print(f"[OCR] Analiza zakończona w {(end - start):.2f}s\n")
        return detected

    def _find_best_match(self, plates: list[str]) -> Tuple[Optional["Report"], Optional[str], float]:
        if not plates:
            return None, None, 0.0

        candidates = list(Report.objects.exclude(status=Report.Status.CLOSED))
        if not candidates:
            return None, None, 0.0

        norm_map = [(r, self._normalize(r.vehicle_plate)) for r in candidates] # Normalizujemy tablice raportów
        for p in plates: # Najpierw szukamy idealnego dopasowania
            np = self._normalize(p) # Normalizujemy wykrytą tablicę
            for r, rv in norm_map: # Porównujemy z normalizowanymi tablicami raportów
                if rv == np: # Idealne dopasowanie
                    return r, p, 100.0 # Zwracamy raport, tablicę i 100% pewności

        best = (None, None, 0.0) # Szukamy najlepszego dopasowania z pewnością poniżej 100%
        for p in plates: # Dla każdej wykrytej tablicy
            np = self._normalize(p) # Normalizujemy tablicę
            for r, rv in norm_map: # Porównujemy z normalizowanymi tablicami raportów
                ratio = SequenceMatcher(None, rv, np).ratio() # Obliczamy podobieństwo
                if ratio > best[2]: # Jeżeli to najlepsze dopasowanie jak dotąd
                    best = (r, p, ratio * 100.0) # Aktualizujemy najlepsze dopasowanie
        return best if best[2] >= 70 else (None, None, 0.0) # Zwracamy tylko jeśli pewność >= 70%

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)

        if is_new or (self.photo or self.video):
            print("[EVIDENCE] Uruchamianie OCR i dopasowania...")
            plates = self._run_ocr()
            self.detected_plates_json = json.dumps(plates, ensure_ascii=False)

            report, plate, conf = self._find_best_match(plates)

            if report and conf == 100.0:
                self.matched_report = report
                self.match_confidence = conf
                self.status = self.Status.MATCHED
                report.vehicle_plate_detected = plate
                report.status = Report.Status.MATCHED
                report.save(update_fields=["vehicle_plate_detected", "status"])
                print(f"[OCR] Tablica {plate} dopasowana do {report.ticket_number}")
            elif report and conf >= 70.0:
                self.matched_report = report
                self.match_confidence = conf
                self.status = self.Status.UNCERTAIN
                report.vehicle_plate_detected = plate
                report.status = Report.Status.UNCERTAIN
                report.save(update_fields=["vehicle_plate_detected", "status"])
                print(f"[OCR] Tablica {plate} częściowo dopasowana do {report.ticket_number}")
            else:
                self.status = self.Status.UNMATCHED
                print("[OCR] Brak dopasowania.")

            super().save(update_fields=["detected_plates_json", "matched_report", "match_confidence", "status"])

    def __str__(self):
        kind = "foto" if self.photo else "video" if self.video else "plik"
        return f"Evidence {self.id} ({kind})"


# CZYSZCZENIE STARYCH PLIKÓW -------------------------------------
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver


@receiver(post_delete, sender=Evidence)
def delete_evidence_files(sender, instance, **kwargs):
    """Usuwa pliki z dysku po usunięciu rekordu Evidence."""
    for field_name in ['photo', 'video']:
        file_field = getattr(instance, field_name)
        if file_field and file_field.name and os.path.isfile(file_field.path):
            try:
                os.remove(file_field.path)
                print(f"🗑️ Usunięto plik: {file_field.path}")
            except Exception as e:
                print(f"⚠️ Nie udało się usunąć {file_field.path}: {e}")


@receiver(pre_save, sender=Evidence)
def delete_old_evidence_files_on_change(sender, instance, **kwargs):
    """Usuwa stary plik, jeśli admin kliknął 'Clear' lub zmienił plik."""
    if not instance.pk:
        return
    try:
        old_instance = Evidence.objects.get(pk=instance.pk)
    except Evidence.DoesNotExist:
        return
    for field_name in ['photo', 'video']:
        old_file = getattr(old_instance, field_name)
        new_file = getattr(instance, field_name)
        if old_file and old_file.name:
            if not new_file or old_file.name != new_file.name:
                if os.path.isfile(old_file.path):
                    try:
                        os.remove(old_file.path)
                        print(f"🧹 Usunięto stary plik (Evidence): {old_file.path}")
                    except Exception as e:
                        print(f"⚠️ Błąd przy czyszczeniu {old_file.path}: {e}")


@receiver(pre_save, sender=Report)
def delete_old_report_files_on_change(sender, instance, **kwargs):
    """Usuwa pliki zdjęć/wideo z raportu, gdy są czyszczone lub podmieniane."""
    if not instance.pk:
        return
    try:
        old_instance = Report.objects.get(pk=instance.pk)
    except Report.DoesNotExist:
        return
    for field_name in ['photo', 'video']:
        old_file = getattr(old_instance, field_name)
        new_file = getattr(instance, field_name)
        if old_file and old_file.name:
            if not new_file or old_file.name != new_file.name:
                if os.path.isfile(old_file.path):
                    try:
                        os.remove(old_file.path)
                        print(f"🧹 Usunięto stary plik (Report): {old_file.path}")
                    except Exception as e:
                        print(f"⚠️ Błąd przy czyszczeniu {old_file.path}: {e}")
