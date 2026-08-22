import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.template.loader import render_to_string

from .models import Complaint, ComplaintTimelineEntry

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

    # 2) Notifikasi ke PIC/Staff cabang terkait
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
# Notifikasi WHATSAPP - STUB
# Ganti implementasi ini dengan provider pilihan Anda (Fonnte, Twilio,
# WhatsApp Business Cloud API, dll). Saat ini hanya logging jika dinonaktifkan.
# =============================================================================
def send_whatsapp_notification(complaint, message, to_staff=False):
    if not settings.WHATSAPP_NOTIFICATIONS_ENABLED:
        logger.info('[WhatsApp stub] (nonaktif) Pesan untuk %s: %s', complaint.code, message)
        return

    phone_number = None
    if to_staff:
        first_pic = complaint.branch.staff_members.filter(is_active_pic=True).first()
        if first_pic:
            phone_number = first_pic.phone
    else:
        phone_number = complaint.customer_phone

    if not phone_number:
        return

    try:
        import requests  # import lokal agar tidak wajib terpasang jika fitur nonaktif
        requests.post(
            settings.WHATSAPP_API_URL,
            headers={'Authorization': f'Bearer {settings.WHATSAPP_API_TOKEN}'},
            json={'phone': phone_number, 'message': message},
            timeout=10,
        )
    except Exception:
        logger.exception('Gagal mengirim notifikasi WhatsApp untuk %s', complaint.code)
