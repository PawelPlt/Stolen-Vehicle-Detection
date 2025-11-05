from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from reports.models import Report

User = get_user_model()

@receiver(post_save, sender=User)
def link_reports_to_new_user(sender, instance, created, **kwargs):
    if created:
        reports = Report.objects.filter(created_by__isnull=True, owner_email__iexact=instance.email)
        if reports.exists():
            reports.update(created_by=instance)
            print(f"[INFO] Powiązano {reports.count()} zgłoszeń z kontem: {instance.email}")
