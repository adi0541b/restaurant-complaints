import time

from django.core.management.base import BaseCommand

from complaints.models import Complaint
from complaints.signals import sync_to_google_sheets


class Command(BaseCommand):
    help = (
        'Sinkron ULANG SEMUA komplain (apa pun statusnya) ke sheet Backup '
        'Google Sheets, dari yang paling lama ke paling baru. Jalankan '
        'perintah ini SEKALI SAJA setelah mengosongkan sheet Backup (lewat '
        'fungsi resetBackupSheet di Apps Script), untuk mengisi ulang semua '
        'data dari awal.'
    )

    def handle(self, *args, **options):
        qs = Complaint.objects.all().order_by('created_at')
        total = qs.count()

        count = 0
        for complaint in qs:
            if count > 0:
                time.sleep(1)  # jaga-jaga hindari rate limit Google Apps Script
            sync_to_google_sheets(complaint)
            count += 1
            self.stdout.write(f'  [{count}/{total}] {complaint.code} disinkronkan.')

        self.stdout.write(self.style.SUCCESS(
            f'Selesai. {count} komplain berhasil disinkronkan ulang ke Google Sheets.'
        ))
