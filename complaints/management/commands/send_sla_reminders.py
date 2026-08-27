from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from complaints.models import Complaint
from complaints.signals import notify_qc_trainers


class Command(BaseCommand):
    help = (
        'Kirim reminder WhatsApp ke QC/Trainer untuk komplain yang akan melewati '
        'batas SLA dalam 3 jam ke depan. Jalankan perintah ini secara BERKALA lewat '
        'cron job (disarankan setiap 15-30 menit) -- lihat DEPLOY_WEBUZO.md untuk '
        'cara setup cron job di panel Webuzo.'
    )

    def handle(self, *args, **options):
        now = timezone.now()
        window_end = now + timedelta(hours=3)

        qs = Complaint.objects.filter(
            sla_reminder_sent=False,
            sla_deadline__isnull=False,
            sla_deadline__gte=now,
            sla_deadline__lte=window_end,
        ).exclude(status__in=[Complaint.Status.SELESAI, Complaint.Status.DITOLAK])

        count = 0
        for complaint in qs:
            sisa_jam = round((complaint.sla_deadline - now).total_seconds() / 3600, 1)
            message = (
                f'⏰ Peringatan SLA: Komplain {complaint.code} di {complaint.branch.name} '
                f'akan melewati batas SLA dalam sekitar {sisa_jam} jam.\n'
                f'Status saat ini: {complaint.get_status_display()}\n'
                f'Tingkat: {complaint.get_severity_display()}\n'
                f'Batas SLA: {timezone.localtime(complaint.sla_deadline).strftime("%d-%m-%Y %H:%M")}\n'
                f'Segera tindak lanjuti agar tidak melewati SLA.'
            )
            notify_qc_trainers(complaint, message)
            complaint.sla_reminder_sent = True
            complaint.save(update_fields=['sla_reminder_sent'])
            count += 1

        self.stdout.write(self.style.SUCCESS(f'{count} reminder SLA terkirim ke QC/Trainer.'))
