from datetime import timedelta
import time

from django.core.management.base import BaseCommand
from django.utils import timezone

from complaints.models import Complaint
from complaints.signals import notify_branch_pics, notify_qc_trainers


class Command(BaseCommand):
    help = (
        'Kirim reminder WhatsApp ke QC/Trainer DAN Leader Outlet untuk komplain '
        'yang sudah 12 jam berjalan tapi kolom Solusi belum diisi. Jalankan '
        'perintah ini secara BERKALA lewat cron job (disarankan setiap 15-30 '
        'menit) -- lihat DEPLOY_WEBUZO.md untuk cara setup cron job di panel Webuzo.'
    )

    def handle(self, *args, **options):
        now = timezone.now()
        cutoff = now - timedelta(hours=12)

        qs = Complaint.objects.filter(
            solution_reminder_sent=False,
            internal_notes='',
            created_at__lte=cutoff,
        ).exclude(status__in=[Complaint.Status.SELESAI, Complaint.Status.DITOLAK])

        count = 0
        for complaint in qs:
            if count > 0:
                time.sleep(2)  # jaga-jaga hindari rate limit provider WhatsApp

            jam_berjalan = round((now - complaint.created_at).total_seconds() / 3600, 1)
            message = (
                f'⚠️ Peringatan: Komplain {complaint.code} di {complaint.branch.name} '
                f'sudah berjalan {jam_berjalan} jam tapi kolom Solusi BELUM diisi.\n'
                f'Status saat ini: {complaint.get_status_display()}\n'
                f'Dilaporkan pada: {timezone.localtime(complaint.created_at).strftime("%d-%m-%Y %H:%M")}\n'
                f'Segera isi Akar Masalah & Solusi.'
            )
            notify_qc_trainers(complaint, message)
            time.sleep(6)  # jeda sebelum kirim ke penerima kelompok berikutnya (Leader Outlet)
            notify_branch_pics(complaint, message)

            complaint.solution_reminder_sent = True
            complaint.save(update_fields=['solution_reminder_sent'])
            count += 1

        self.stdout.write(self.style.SUCCESS(
            f'{count} reminder Solusi (12 jam) terkirim ke QC/Trainer & Leader Outlet.'
        ))
