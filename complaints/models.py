from datetime import timedelta

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


# =============================================================================
# CABANG (BRANCH)
# =============================================================================
class Branch(models.Model):
    """Cabang restoran."""
    name = models.CharField('Nama Cabang', max_length=150)
    code = models.CharField('Kode Cabang', max_length=20, unique=True,
                             help_text='Contoh: JKT-01, BDG-02')
    address = models.TextField('Alamat', blank=True)
    city = models.CharField('Kota', max_length=100, blank=True)
    phone = models.CharField('Telepon', max_length=30, blank=True)
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name='Manager Cabang',
        related_name='branches_managed', null=True, blank=True,
        on_delete=models.SET_NULL,
    )
    is_active = models.BooleanField('Aktif', default=True)
    created_at = models.DateTimeField('Dibuat pada', auto_now_add=True)

    class Meta:
        verbose_name = 'Cabang'
        verbose_name_plural = 'Cabang'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.code})'


# =============================================================================
# PROFIL STAFF / PIC
# =============================================================================
class StaffProfile(models.Model):
    """Profil tambahan untuk user dengan peran Staff/PIC, Manager, atau Admin Pusat."""

    class Role(models.TextChoices):
        STAFF = 'staff', 'Staff / PIC Cabang'
        MANAGER = 'manager', 'Manager Cabang'
        ADMIN = 'admin', 'Admin Pusat'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, verbose_name='Akun Pengguna',
        related_name='staff_profile', on_delete=models.CASCADE,
    )
    role = models.CharField('Peran', max_length=20, choices=Role.choices, default=Role.STAFF)
    branch = models.ForeignKey(
        Branch, verbose_name='Cabang', related_name='staff_members',
        null=True, blank=True, on_delete=models.SET_NULL,
        help_text='Kosongkan untuk Admin Pusat (akses semua cabang).',
    )
    phone = models.CharField('No. WhatsApp', max_length=30, blank=True)
    photo = models.ImageField('Foto Profil', upload_to='staff_photos/', blank=True, null=True)
    is_active_pic = models.BooleanField('Aktif Menerima Komplain', default=True)
    created_at = models.DateTimeField('Dibuat pada', auto_now_add=True)

    class Meta:
        verbose_name = 'Profil Staff'
        verbose_name_plural = 'Profil Staff'

    def __str__(self):
        branch_label = self.branch.name if self.branch else 'Semua Cabang'
        return f'{self.user.get_full_name() or self.user.username} - {self.get_role_display()} ({branch_label})'

    @property
    def is_admin_pusat(self):
        return self.role == self.Role.ADMIN

    @property
    def is_manager(self):
        return self.role == self.Role.MANAGER

    @property
    def is_staff_pic(self):
        return self.role == self.Role.STAFF


# =============================================================================
# KOMPLAIN
# =============================================================================
class Complaint(models.Model):
    """Komplain pelanggan."""

    class Severity(models.TextChoices):
        KRITIS = 'kritis', 'Kritis'
        TINGGI = 'tinggi', 'Tinggi'
        SEDANG = 'sedang', 'Sedang'
        RENDAH = 'rendah', 'Rendah'

    class Category(models.TextChoices):
        MAKANAN = 'makanan', 'Kualitas Makanan'
        PELAYANAN = 'pelayanan', 'Pelayanan Staff'
        KEBERSIHAN = 'kebersihan', 'Kebersihan'
        KECEPATAN = 'kecepatan', 'Kecepatan Penyajian'
        FASILITAS = 'fasilitas', 'Fasilitas / Kenyamanan'
        PEMBAYARAN = 'pembayaran', 'Pembayaran / Struk'
        LAINNYA = 'lainnya', 'Lainnya'

    class Status(models.TextChoices):
        BARU = 'baru', 'Baru'
        DITINJAU = 'ditinjau', 'Sedang Ditinjau'
        DIPROSES = 'diproses', 'Sedang Diproses'
        SELESAI = 'selesai', 'Selesai'
        DITOLAK = 'ditolak', 'Ditolak'

    # --- Identitas & keterlacakan -------------------------------------------------
    code = models.CharField('Kode Komplain', max_length=20, unique=True, editable=False,
                             help_text='Auto-generate, contoh: CMP-00001')

    # --- Data pelapor ---------------------------------------------------------
    customer_name = models.CharField('Nama Pelanggan', max_length=150)
    customer_phone = models.CharField('No. HP / WhatsApp', max_length=30)
    customer_email = models.EmailField('Email', blank=True)

    # --- Konteks kejadian (mendukung prefill lewat QR code / URL) -------------
    branch = models.ForeignKey(Branch, verbose_name='Cabang', related_name='complaints',
                                on_delete=models.PROTECT)
    table_number = models.CharField('Nomor Meja', max_length=20, blank=True)
    visit_date = models.DateField('Tanggal Kunjungan', null=True, blank=True)
    order_number = models.CharField('Nomor Pesanan/Struk', max_length=50, blank=True)

    # --- Isi komplain -----------------------------------------------------------
    category = models.CharField('Kategori', max_length=20, choices=Category.choices)
    severity = models.CharField('Tingkat Keparahan', max_length=10, choices=Severity.choices,
                                 default=Severity.SEDANG)
    description = models.TextField('Deskripsi Komplain')
    photo_evidence = models.ImageField('Foto Bukti', upload_to='complaint_photos/%Y/%m/',
                                        blank=True, null=True)

    # --- Penanganan --------------------------------------------------------
    status = models.CharField('Status', max_length=15, choices=Status.choices, default=Status.BARU)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name='Ditangani oleh',
        related_name='complaints_assigned', null=True, blank=True,
        on_delete=models.SET_NULL,
    )
    resolution_notes = models.TextField('Catatan Penyelesaian', blank=True)
    internal_notes = models.TextField('Catatan Internal (tidak terlihat pelanggan)', blank=True)

    # --- SLA ------------------------------------------------------------------
    sla_deadline = models.DateTimeField('Batas Waktu SLA', null=True, blank=True, editable=False)
    resolved_at = models.DateTimeField('Selesai pada', null=True, blank=True)

    # --- Kepuasan pelanggan ------------------------------------------------
    satisfaction_rating = models.PositiveSmallIntegerField(
        'Rating Kepuasan (1-5)', null=True, blank=True,
    )
    satisfaction_feedback = models.TextField('Masukan Tambahan', blank=True)
    rated_at = models.DateTimeField('Dinilai pada', null=True, blank=True)

    # --- Metadata ---------------------------------------------------------
    created_at = models.DateTimeField('Dibuat pada', auto_now_add=True)
    updated_at = models.DateTimeField('Diperbarui pada', auto_now=True)

    class Meta:
        verbose_name = 'Komplain'
        verbose_name_plural = 'Komplain'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.code} - {self.customer_name} ({self.get_status_display()})'

    def get_absolute_url(self):
        return reverse('complaints:complaint_detail', kwargs={'pk': self.pk})

    # ------------------------------------------------------------------
    # Kode komplain otomatis: CMP-00001, CMP-00002, dst.
    # ------------------------------------------------------------------
    @staticmethod
    def generate_code():
        last = Complaint.objects.order_by('-id').first()
        next_number = (last.id + 1) if last else 1
        return f'CMP-{next_number:05d}'

    # ------------------------------------------------------------------
    # SLA per tingkat keparahan (jam), lihat settings.SLA_HOURS
    # ------------------------------------------------------------------
    def calculate_sla_deadline(self):
        from django.conf import settings as dj_settings
        hours = dj_settings.SLA_HOURS.get(self.severity, 24)
        base_time = self.created_at or timezone.now()
        return base_time + timedelta(hours=hours)

    @property
    def is_overdue(self):
        if self.status in (self.Status.SELESAI, self.Status.DITOLAK):
            return False
        if not self.sla_deadline:
            return False
        return timezone.now() > self.sla_deadline

    @property
    def time_remaining(self):
        """Sisa waktu SLA (timedelta), negatif jika sudah lewat."""
        if not self.sla_deadline:
            return None
        return self.sla_deadline - timezone.now()

    @property
    def sla_progress_percent(self):
        """Persentase waktu SLA yang telah terpakai, untuk progress bar UI."""
        if not self.sla_deadline or not self.created_at:
            return 0
        total = (self.sla_deadline - self.created_at).total_seconds()
        used = (timezone.now() - self.created_at).total_seconds()
        if total <= 0:
            return 100
        return max(0, min(100, round((used / total) * 100)))

    def mark_resolved(self):
        self.status = self.Status.SELESAI
        self.resolved_at = timezone.now()

    def save(self, *args, **kwargs):
        is_new = self._state.adding

        if is_new and not self.code:
            self.code = self.generate_code()

        # created_at belum tersedia sebelum penyimpanan pertama; hitung ulang
        # sla_deadline setelah created_at diketahui, atau saat severity berubah.
        super().save(*args, **kwargs)

        if is_new or not self.sla_deadline:
            self.sla_deadline = self.calculate_sla_deadline()
            super().save(update_fields=['sla_deadline'])


class ComplaintTimelineEntry(models.Model):
    """Riwayat/log perubahan status suatu komplain, untuk transparansi ke pelanggan & staff."""
    complaint = models.ForeignKey(Complaint, verbose_name='Komplain', related_name='timeline',
                                   on_delete=models.CASCADE)
    old_status = models.CharField('Status Lama', max_length=15, blank=True)
    new_status = models.CharField('Status Baru', max_length=15)
    note = models.TextField('Catatan', blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name='Diubah oleh', null=True, blank=True,
        on_delete=models.SET_NULL,
    )
    created_at = models.DateTimeField('Waktu', auto_now_add=True)

    class Meta:
        verbose_name = 'Riwayat Status'
        verbose_name_plural = 'Riwayat Status'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.complaint.code}: {self.old_status} -> {self.new_status}'


# =============================================================================
# PENGATURAN SITUS (nama perusahaan & logo) - hanya boleh diubah Admin Pusat
# =============================================================================
class SiteSettings(models.Model):
    """Singleton: menyimpan identitas perusahaan yang bisa diubah dari panel admin."""
    company_name = models.CharField('Nama Perusahaan', max_length=150, default='Rasa Nusantara')
    logo = models.ImageField('Logo Perusahaan', upload_to='site/', blank=True, null=True)
    updated_at = models.DateTimeField('Diperbarui pada', auto_now=True)

    class Meta:
        verbose_name = 'Pengaturan Situs'
        verbose_name_plural = 'Pengaturan Situs'

    def __str__(self):
        return self.company_name

    def save(self, *args, **kwargs):
        self.pk = 1  # paksa selalu menjadi baris tunggal (singleton)
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
