import logging
import time

from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.utils import timezone

from .models import Complaint, ComplaintTimelineEntry, StaffProfile

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Complaint)
def _stash_old_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            instance._old_status = Complaint.objects.get(pk=instance.pk).status
        except Complaint.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender=Complaint)
def notify_on_complaint_change(sender, instance, created, **kwargs):
    # Sinkron ke Google Sheets (backup lengkap 31 kolom) SETIAP kali komplain
    # disimpan -- baik baru dibuat maupun diubah (update/upsert berdasarkan
    # Kode, bukan cuma sekali saat Deadline lewat seperti sebelumnya).
    sync_to_google_sheets(instance)

    old_status = getattr(instance, '_old_status', None)

    if created:
        ComplaintTimelineEntry.objects.create(
            complaint=instance, old_status='', new_status=instance.status,
            note='Komplain baru diterima.',
        )
        send_new_complaint_notifications(instance)
        return

    if old_status is not None and old_status != instance.status:
        ComplaintTimelineEntry.objects.create(
            complaint=instance, old_status=old_status, new_status=instance.status,
        )
        # Catatan: pelanggan SENGAJA tidak lagi dikirimi notifikasi apa pun
        # (email/WhatsApp) saat status komplain berubah.


def send_new_complaint_notifications(complaint):
    # Kirim data ke sheet "Rekap" (Kota/Outlet/Komplain Produk/Komplain Servis)
    # SETIAP ada komplain baru -- otomatis nambah 1 ke kolom yang sesuai.
    sync_to_rekap_sheet(complaint)

    if complaint.customer_email:
        try:
            send_mail(
                subject=f'Komplain Anda Diterima - {complaint.code}',
                message=(
                    f'Halo {complaint.customer_name},\n\n'
                    f'Terima kasih telah menyampaikan komplain Anda di {complaint.branch.name}.\n'
                    f'Kode komplain Anda: {complaint.code}\n'
                    f'Gunakan kode ini untuk mengecek status penanganan kapan saja.\n\n'
                    f'Tim kami akan segera menindaklanjuti.\n\n'
                    f'Salam,\nTim Layanan Pelanggan'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[complaint.customer_email],
                fail_silently=True,
            )
        except Exception:
            logger.exception('Gagal mengirim email konfirmasi ke pelanggan untuk %s', complaint.code)

    staff_emails = list(
        complaint.branch.staff_members.filter(
            is_active_pic=True
        ).exclude(user__email='').values_list('user__email', flat=True)
    )
    if staff_emails:
        try:
            send_mail(
                subject=f'[Komplain Baru] {complaint.code}',
                message=(
                    f'Ada komplain baru masuk di {complaint.branch.name}.\n\n'
                    f'Kode: {complaint.code}\n'
                    f'Kategori: {complaint.get_category_display()}\n'
                    f'Batas Deadline: {timezone.localtime(complaint.sla_deadline).strftime("%d-%m-%Y %H:%M") if complaint.sla_deadline else "-"}\n\n'
                    f'Deskripsi: {complaint.description}\n\n'
                    f'Segera tindak lanjuti melalui dashboard.'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=staff_emails,
                fail_silently=True,
            )
        except Exception:
            logger.exception('Gagal mengirim email notifikasi staff untuk %s', complaint.code)

    send_whatsapp_notification(
        complaint,
        f'Komplain baru {complaint.code} masuk di {complaint.branch.name}. '
        f'Segera tindak lanjuti.',
        to_staff=True,
    )

    time.sleep(6)

    notify_qc_trainers(
        complaint,
        f'[BARU] Komplain baru {complaint.code} masuk di {complaint.branch.name} '
        f'(Kota {complaint.branch.city.name if complaint.branch.city else "-"}).\n'
        f'Jenis: {complaint.get_category_display()}'
        f'{" - " + complaint.detail_item.name if complaint.detail_item else ""}\n'
        f'Batas Deadline: {timezone.localtime(complaint.sla_deadline).strftime("%d-%m-%Y %H:%M") if complaint.sla_deadline else "-"}\n'
        f'Deskripsi: {complaint.description}'
    )


def send_whatsapp_message(phone_number, message, log_ref=''):
    """Fungsi generik: kirim satu pesan WhatsApp ke satu nomor tertentu."""
    if not settings.WHATSAPP_NOTIFICATIONS_ENABLED:
        logger.info('[WhatsApp stub] (nonaktif) Pesan %s untuk %s: %s', log_ref, phone_number, message)
        return

    if not phone_number:
        return

    normalized_phone = phone_number.strip().replace(' ', '').replace('-', '')
    if normalized_phone.startswith('0'):
        normalized_phone = '62' + normalized_phone[1:]
    elif normalized_phone.startswith('+'):
        normalized_phone = normalized_phone[1:]

    try:
        import requests
        response = requests.post(
            settings.WHATSAPP_API_URL,
            headers={'Authorization': settings.WHATSAPP_API_TOKEN},
            data={'target': normalized_phone, 'message': message},
            timeout=10,
        )
        logger.info('[WhatsApp] Respons Fonnte %s: %s', log_ref, response.text[:300])
    except Exception:
        logger.exception('Gagal mengirim notifikasi WhatsApp %s', log_ref)


def send_whatsapp_notification(complaint, message, to_staff=False):
    phone_number = None
    if to_staff:
        first_pic = complaint.branch.staff_members.filter(is_active_pic=True).first()
        if first_pic:
            phone_number = first_pic.phone
    else:
        phone_number = complaint.customer_phone

    send_whatsapp_message(phone_number, message, log_ref=complaint.code)


def notify_qc_trainers(complaint, message):
    city = complaint.branch.city if complaint.branch else None
    if not city:
        logger.info(
            '[WhatsApp] Outlet %s belum diset kotanya, notifikasi QC/Trainer untuk %s dilewati.',
            complaint.branch, complaint.code,
        )
        return

    qc_trainers = list(StaffProfile.objects.filter(
        role=StaffProfile.Role.QC_TRAINER, city=city,
    ).exclude(phone=''))

    for index, profile in enumerate(qc_trainers):
        if index > 0:
            time.sleep(6)
        send_whatsapp_message(profile.phone, message, log_ref=f'{complaint.code} -> QC/Trainer {profile.user}')


def notify_branch_pics(complaint, message):
    if not complaint.branch:
        return

    pics = list(complaint.branch.staff_members.filter(is_active_pic=True).exclude(phone=''))

    for index, profile in enumerate(pics):
        if index > 0:
            time.sleep(6)
        send_whatsapp_message(profile.phone, message, log_ref=f'{complaint.code} -> Leader Outlet {profile.user}')


# =============================================================================
# Backup otomatis ke GOOGLE SHEETS via Google Apps Script Web App
# =============================================================================
def sync_to_google_sheets(complaint):
    """Kirim satu baris data komplain ke Google Sheets (backup), dengan kolom
    PERSIS SAMA dengan export Excel. Gagal secara diam-diam (dicatat di log
    saja) supaya tidak pernah mengganggu alur utama kalau Google Sheets
    sedang bermasalah."""
    webhook_url = getattr(settings, 'GOOGLE_SHEETS_WEBHOOK_URL', '')
    if not webhook_url:
        logger.info('[Google Sheets] GOOGLE_SHEETS_WEBHOOK_URL kosong, backup untuk %s dilewati.', complaint.code)
        return

    def _fmt(dt):
        return timezone.localtime(dt).strftime('%d-%m-%Y %H:%M') if dt else ''

    payload = {
        'kode': complaint.code,
        'nama_pelanggan': complaint.customer_name,
        'no_hp': complaint.customer_phone,
        'email': complaint.customer_email,
        'kota': complaint.branch.city.name if complaint.branch and complaint.branch.city else '',
        'outlet': complaint.branch.name if complaint.branch else '',
        'no_meja': complaint.table_number,
        'tanggal_kunjungan': complaint.visit_date.strftime('%d-%m-%Y') if complaint.visit_date else '',
        'no_pesanan': complaint.order_number,
        'sumber_komplain': str(complaint.source) if complaint.source else '',
        'jam_komplain_masuk': _fmt(complaint.customer_complaint_time),
        'jam_ditangani_cs': _fmt(complaint.cs_handled_time),
        'jenis_komplain': complaint.get_category_display(),
        'rincian_komplain': complaint.detail_item.name if complaint.detail_item else '',
        'tingkat_keparahan': complaint.get_severity_display(),
        'status': complaint.get_status_display(),
        'deskripsi': complaint.description,
        'ditangani_oleh': str(complaint.assigned_to) if complaint.assigned_to else '',
        'akar_masalah': complaint.resolution_notes,
        'akar_masalah_diisi_pada': _fmt(complaint.resolution_notes_filled_at),
        'solusi': complaint.internal_notes,
        'solusi_diisi_pada': _fmt(complaint.internal_notes_filled_at),
        'quality_alert': complaint.quality_alert,
        'quality_alert_diisi_pada': _fmt(complaint.quality_alert_filled_at),
        'validasi': complaint.validation_notes,
        'validasi_diisi_pada': _fmt(complaint.validation_notes_filled_at),
        'dilaporkan_pada': _fmt(complaint.created_at),
        'batas_deadline': _fmt(complaint.sla_deadline),
        'lewat_deadline': 'Ya' if complaint.is_overdue else 'Tidak',
        'selesai_pada': _fmt(complaint.resolved_at),
        'rating_kepuasan': complaint.satisfaction_rating,
        'masukan_tambahan': complaint.satisfaction_feedback,
    }

    try:
        import requests
        response = requests.post(webhook_url, json=payload, timeout=15)
        logger.info('[Google Sheets] Respons backup untuk %s: %s', complaint.code, response.text[:300])
    except Exception:
        logger.exception('Gagal backup ke Google Sheets untuk %s', complaint.code)


# =============================================================================
# Sinkron REKAP (Kota/Outlet/Komplain Produk/Komplain Servis) via Google Apps
# Script Web App terpisah -- terkirim SETIAP ada komplain baru (bukan cuma
# saat Deadline lewat), otomatis menambah 1 ke kolom yang sesuai di sheet.
# Sheet-nya sendiri otomatis reset ke 0 tiap tanggal 26 (diatur di Apps Script).
# =============================================================================
def sync_to_rekap_sheet(complaint):
    webhook_url = getattr(settings, 'GOOGLE_SHEETS_REKAP_WEBHOOK_URL', '')
    if not webhook_url:
        logger.info('[Google Sheets Rekap] GOOGLE_SHEETS_REKAP_WEBHOOK_URL kosong, sinkron untuk %s dilewati.', complaint.code)
        return

    payload = {
        'kota': complaint.branch.city.name if complaint.branch and complaint.branch.city else '',
        'outlet': complaint.branch.name if complaint.branch else '',
        'jenis': 'produk' if complaint.category == Complaint.Category.PRODUK else 'servis',
    }

    try:
        import requests
        response = requests.post(webhook_url, json=payload, timeout=15)
        logger.info('[Google Sheets Rekap] Respons untuk %s: %s', complaint.code, response.text[:300])
    except Exception:
        logger.exception('Gagal sinkron Rekap ke Google Sheets untuk %s', complaint.code)
