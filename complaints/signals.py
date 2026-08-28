import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.utils import timezone

from .models import Complaint, ComplaintTimelineEntry, StaffProfile

logger = logging.getLogger(__name__)


# =============================================================================
# Lacak perubahan status untuk membuat entri timeline & memicu notifikasi
# =============================================================================
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
        send_status_update_notification(instance, old_status)


# =============================================================================
# Notifikasi EMAIL (development: console backend, ganti ke SMTP di produksi)
# =============================================================================
def send_new_complaint_notifications(complaint):
    # 1) Konfirmasi ke pelanggan
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

    # 2) Notifikasi ke PIC/Staff outlet terkait
    staff_emails = list(
        complaint.branch.staff_members.filter(
            is_active_pic=True
        ).exclude(user__email='').values_list('user__email', flat=True)
    )
    if staff_emails:
        try:
            send_mail(
                subject=f'[Komplain Baru] {complaint.code} - {complaint.get_severity_display()}',
                message=(
                    f'Ada komplain baru masuk di {complaint.branch.name}.\n\n'
                    f'Kode: {complaint.code}\n'
                    f'Kategori: {complaint.get_category_display()}\n'
                    f'Tingkat: {complaint.get_severity_display()}\n'
                    f'Batas SLA: {complaint.sla_deadline}\n\n'
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
        f'Tingkat: {complaint.get_severity_display()}. Segera tindak lanjuti.',
        to_staff=True,
    )

    # 3) Notifikasi ke WhatsApp QC/Trainer di kota outlet terkait
    notify_qc_trainers(
        complaint,
        f'📥 Komplain baru {complaint.code} masuk di {complaint.branch.name} '
        f'(Kota {complaint.branch.city.name if complaint.branch.city else "-"}).\n'
        f'Jenis: {complaint.get_category_display()}'
        f'{" - " + complaint.detail_item.name if complaint.detail_item else ""}\n'
        f'Tingkat: {complaint.get_severity_display()}\n'
        f'Batas SLA: {timezone.localtime(complaint.sla_deadline).strftime("%d-%m-%Y %H:%M") if complaint.sla_deadline else "-"}\n'
        f'Deskripsi: {complaint.description}'
    )


def send_status_update_notification(complaint, old_status):
    if complaint.customer_email:
        try:
            send_mail(
                subject=f'Update Status Komplain {complaint.code}',
                message=(
                    f'Halo {complaint.customer_name},\n\n'
                    f'Status komplain Anda ({complaint.code}) telah diperbarui menjadi: '
                    f'{complaint.get_status_display()}.\n\n'
                    + (f'Catatan: {complaint.resolution_notes}\n\n' if complaint.resolution_notes else '')
                    + 'Cek status lengkap kapan saja di halaman "Cek Status Komplain".\n\n'
                    'Salam,\nTim Layanan Pelanggan'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[complaint.customer_email],
                fail_silently=True,
            )
        except Exception:
            logger.exception('Gagal mengirim email update status untuk %s', complaint.code)

    send_whatsapp_notification(
        complaint,
        f'Status komplain {complaint.code} Anda kini: {complaint.get_status_display()}.',
        to_staff=False,
    )


# =============================================================================
# Notifikasi WHATSAPP via TextMeBot (https://textmebot.com)
# Kalau ingin pindah ke provider lain (Fonnte, Twilio, WA Cloud API resmi, dll),
# sesuaikan format request di bawah ini dengan dokumentasi provider tersebut.
# =============================================================================
def send_whatsapp_message(phone_number, message, log_ref=''):
    """Fungsi generik: kirim satu pesan WhatsApp ke satu nomor tertentu."""
    if not settings.WHATSAPP_NOTIFICATIONS_ENABLED:
        logger.info('[WhatsApp stub] (nonaktif) Pesan %s untuk %s: %s', log_ref, phone_number, message)
        return

    if not phone_number:
        return

    # TextMeBot butuh format nomor internasional DENGAN tanda "+" (mis. +628123456789).
    # Ubah otomatis dari format lokal "08..." kalau perlu.
    normalized_phone = phone_number.strip().replace(' ', '').replace('-', '')
    if normalized_phone.startswith('0'):
        normalized_phone = '+62' + normalized_phone[1:]
    elif normalized_phone.startswith('62'):
        normalized_phone = '+' + normalized_phone
    elif not normalized_phone.startswith('+'):
        normalized_phone = '+' + normalized_phone

    try:
        import requests  # import lokal agar tidak wajib terpasang jika fitur nonaktif
        response = requests.get(
            settings.WHATSAPP_API_URL,
            params={
                'recipient': normalized_phone,
                'apikey': settings.WHATSAPP_API_TOKEN,
                'text': message,
            },
            timeout=10,
        )
        logger.info('[WhatsApp] Respons TextMeBot %s: %s', log_ref, response.text[:300])
    except Exception:
        logger.exception('Gagal mengirim notifikasi WhatsApp %s', log_ref)


def send_whatsapp_notification(complaint, message, to_staff=False):
    """Kirim WhatsApp terkait komplain: ke Staff/PIC outlet (to_staff=True) atau ke pelanggan."""
    phone_number = None
    if to_staff:
        first_pic = complaint.branch.staff_members.filter(is_active_pic=True).first()
        if first_pic:
            phone_number = first_pic.phone
    else:
        phone_number = complaint.customer_phone

    send_whatsapp_message(phone_number, message, log_ref=complaint.code)


def notify_qc_trainers(complaint, message):
    """Kirim WhatsApp ke SEMUA QC/Trainer yang cakupan kotanya sama dengan
    kota outlet komplain ini."""
    city = complaint.branch.city if complaint.branch else None
    if not city:
        logger.info(
            '[WhatsApp] Outlet %s belum diset kotanya, notifikasi QC/Trainer untuk %s dilewati.',
            complaint.branch, complaint.code,
        )
        return

    qc_trainers = StaffProfile.objects.filter(
        role=StaffProfile.Role.QC_TRAINER, city=city,
    ).exclude(phone='')

    for profile in qc_trainers:
        send_whatsapp_message(profile.phone, message, log_ref=f'{complaint.code} -> QC/Trainer {profile.user}')
