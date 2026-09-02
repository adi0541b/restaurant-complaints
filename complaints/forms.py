from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm

from .models import (
    Branch, City, Complaint, ComplaintDetailItem, ComplaintSource,
    SiteSettings, StaffProfile,
)

User = get_user_model()


class ComplaintSubmissionForm(forms.ModelForm):
    """Form input komplain oleh Staff Input Komplain, atas nama pelanggan."""

    class Meta:
        model = Complaint
        fields = [
            'customer_name', 'customer_phone',
            'branch', 'visit_date', 'order_number',
            'customer_complaint_time', 'cs_handled_time', 'source',
            'category', 'detail_item', 'severity', 'description', 'photo_evidence',
        ]
        widgets = {
            'customer_name': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Nama lengkap Customer'}),
            'customer_phone': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': '08xxxxxxxxxx'}),
            'branch': forms.Select(attrs={'class': 'form-select'}),
            'visit_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'order_number': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Nomor struk/pesanan (opsional)'}),
            'customer_complaint_time': forms.DateTimeInput(attrs={
                'class': 'form-control', 'type': 'datetime-local'}),
            'cs_handled_time': forms.DateTimeInput(attrs={
                'class': 'form-control', 'type': 'datetime-local'}),
            'source': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select', 'id': 'id_category'}),
            'detail_item': forms.Select(attrs={'class': 'form-select', 'id': 'id_detail_item'}),
            'severity': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 5,
                'placeholder': 'Ceritakan detail komplain Anda...'}),
            'photo_evidence': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'customer_name': 'Nama Customer',
            'customer_phone': 'No. HP / WhatsApp',
            'category': 'Jenis Komplain',
            'detail_item': 'Rincian Komplain',
            'severity': 'Tingkat Keparahan (menurut Anda)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['branch'].queryset = Branch.objects.filter(is_active=True)
        self.fields['source'].queryset = ComplaintSource.objects.filter(is_active=True)
        self.fields['detail_item'].queryset = ComplaintDetailItem.objects.filter(is_active=True)
        self.fields['order_number'].required = False
        self.fields['visit_date'].required = False
        self.fields['photo_evidence'].required = False
        self.fields['customer_complaint_time'].required = False
        self.fields['cs_handled_time'].required = False
        self.fields['source'].required = False
        self.fields['detail_item'].required = False


class StatusCheckForm(forms.Form):
    """Form pengecekan status komplain oleh pelanggan: kode + no HP."""
    code = forms.CharField(
        label='Kode Komplain', max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CMP-00001'}),
    )
    customer_phone = forms.CharField(
        label='No. HP yang digunakan saat lapor', max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '08xxxxxxxxxx'}),
    )


class SatisfactionRatingForm(forms.ModelForm):
    """Form rating kepuasan setelah komplain selesai ditangani."""

    class Meta:
        model = Complaint
        fields = ['satisfaction_rating', 'satisfaction_feedback']
        widgets = {
            'satisfaction_rating': forms.RadioSelect(choices=[(i, str(i)) for i in range(1, 6)]),
            'satisfaction_feedback': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Ada masukan tambahan untuk kami? (opsional)'}),
        }


class ComplaintUpdateForm(forms.ModelForm):
    """Form memperbarui penanganan komplain. Field yang muncul & bisa diedit
    tergantung PERAN user (profile) dan SEJAUH MANA data sudah terisi
    (tanpa gerbang konfirmasi Validator -- QC/Trainer mengisi berurutan
    sendiri, Validasi otomatis menyelesaikan komplain saat diisi):

    - Status & Tingkat Keparahan : hanya CS (Staff Input Komplain)
    - Akar Masalah               : hanya QC/Trainer
    - Solusi + Foto Solusi (WAJIB) : hanya QC/Trainer, MUNCUL setelah
                                    Akar Masalah terisi
    - Quality Alert + Foto Quality Alert (WAJIB) : hanya QC/Trainer, MUNCUL
                                    setelah Solusi + Foto Solusi terisi
    - Validasi (teks)            : hanya QC/Trainer, MUNCUL setelah SEMUA
                                    kolom di atas terisi lengkap -> saat
                                    diisi & disimpan, status langsung Selesai
    - Tanggapan MA                : hanya Manager Area, kapan saja
    - Tindak Lanjut LO            : hanya Leader Outlet, kapan saja
    """

    class Meta:
        model = Complaint
        fields = [
            'status', 'severity', 'resolution_notes',
            'internal_notes', 'solution_photo',
            'quality_alert', 'quality_alert_photo',
            'validation_notes',
            'manager_response', 'lo_followup',
        ]
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'severity': forms.Select(attrs={'class': 'form-select'}),
            'resolution_notes': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Apa akar penyebab masalah ini?'}),
            'internal_notes': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Solusi/tindakan yang diberikan'}),
            'solution_photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'quality_alert': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Penjelasan Quality Alert'}),
            'quality_alert_photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'validation_notes': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Catatan validasi akhir'}),
            'manager_response': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Masukan/tanggapan Anda terkait komplain ini'}),
            'lo_followup': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Jelaskan tindak lanjut penanganan komplain ini'}),
        }
        labels = {
            'resolution_notes': 'Akar Masalah',
            'internal_notes': 'Solusi',
            'solution_photo': 'Foto Solusi',
            'quality_alert': 'Quality Alert',
            'quality_alert_photo': 'Foto Quality Alert',
            'validation_notes': 'Validasi',
            'manager_response': 'Tanggapan MA',
            'lo_followup': 'Tindak Lanjut LO',
        }

    def __init__(self, *args, **kwargs):
        profile = kwargs.pop('profile', None)
        super().__init__(*args, **kwargs)

        # "Selesai" mengunci semua field QC/Trainer (Akar Masalah, Solusi,
        # Quality Alert, Validasi) supaya tidak bisa diubah-ubah lagi.
        sudah_selesai = bool(self.instance and self.instance.status == Complaint.Status.SELESAI)

        # Status & Tingkat Keparahan: hanya Staff Input Komplain
        if not (profile and profile.is_input_staff):
            del self.fields['status']
            del self.fields['severity']

        # Akar Masalah: hanya QC/Trainer, DAN hanya selama belum Selesai
        if not (profile and profile.can_handle_case) or sudah_selesai:
            if 'resolution_notes' in self.fields:
                del self.fields['resolution_notes']

        # Solusi + Foto Solusi (WAJIB): hanya QC/Trainer, muncul setelah
        # Akar Masalah terisi, DAN hanya selama belum Selesai
        akar_masalah_sudah_terisi = bool(self.instance and self.instance.resolution_notes)
        if 'internal_notes' in self.fields:
            if not (profile and profile.can_handle_case) or not akar_masalah_sudah_terisi or sudah_selesai:
                del self.fields['internal_notes']
            else:
                self.fields['internal_notes'].required = True
        if 'solution_photo' in self.fields:
            if not (profile and profile.can_handle_case) or not akar_masalah_sudah_terisi or sudah_selesai:
                del self.fields['solution_photo']
            else:
                self.fields['solution_photo'].required = not bool(
                    self.instance and self.instance.solution_photo
                )

        # Quality Alert + Foto Quality Alert (WAJIB): hanya QC/Trainer, muncul
        # setelah Solusi + Foto Solusi lengkap terisi, DAN belum Selesai
        solusi_lengkap = bool(
            self.instance and self.instance.internal_notes and self.instance.solution_photo
        )
        if 'quality_alert' in self.fields:
            if not (profile and profile.can_handle_case) or not solusi_lengkap or sudah_selesai:
                del self.fields['quality_alert']
            else:
                self.fields['quality_alert'].required = True
        if 'quality_alert_photo' in self.fields:
            if not (profile and profile.can_handle_case) or not solusi_lengkap or sudah_selesai:
                del self.fields['quality_alert_photo']
            else:
                self.fields['quality_alert_photo'].required = not bool(
                    self.instance and self.instance.quality_alert_photo
                )

        # Validasi (teks): hanya QC/Trainer, muncul setelah SEMUA kolom di
        # atas (Akar Masalah, Solusi+Foto, Quality Alert+Foto) lengkap terisi
        semua_lengkap = bool(
            self.instance and self.instance.resolution_notes
            and self.instance.internal_notes and self.instance.solution_photo
            and self.instance.quality_alert and self.instance.quality_alert_photo
        )
        if 'validation_notes' in self.fields:
            if not (profile and profile.can_handle_case) or not semua_lengkap or sudah_selesai:
                del self.fields['validation_notes']
            else:
                self.fields['validation_notes'].required = True

        # Tanggapan MA: hanya Manager Area, bisa diisi/diubah KAPAN SAJA
        # (tidak terikat tahapan alur Akar Masalah/Solusi/Validasi).
        if 'manager_response' in self.fields:
            if not (profile and profile.is_manager):
                del self.fields['manager_response']

        # Tindak Lanjut LO: hanya Leader Outlet (Staff/PIC Outlet), bisa diisi/
        # diubah KAPAN SAJA (tidak terikat tahapan alur lainnya).
        if 'lo_followup' in self.fields:
            if not (profile and profile.is_staff_pic):
                del self.fields['lo_followup']


# =============================================================================
# PANEL ADMIN PUSAT: kelola akun staff, outlet, dan identitas perusahaan
# =============================================================================
ADMIN_TEXT_ATTRS = {'class': 'form-control'}
ADMIN_SELECT_ATTRS = {'class': 'form-select'}


class StaffAccountCreateForm(UserCreationForm):
    """Form membuat akun baru dengan berbagai peran."""
    first_name = forms.CharField(label='Nama Depan', max_length=150, widget=forms.TextInput(attrs=ADMIN_TEXT_ATTRS))
    last_name = forms.CharField(label='Nama Belakang', max_length=150, required=False,
                                 widget=forms.TextInput(attrs=ADMIN_TEXT_ATTRS))
    email = forms.EmailField(label='Email', required=False, widget=forms.EmailInput(attrs=ADMIN_TEXT_ATTRS))
    role = forms.ChoiceField(label='Peran', choices=StaffProfile.Role.choices, widget=forms.Select(attrs=ADMIN_SELECT_ATTRS))
    branch = forms.ModelChoiceField(
        label='Outlet', queryset=Branch.objects.filter(is_active=True), required=False,
        widget=forms.Select(attrs=ADMIN_SELECT_ATTRS),
        help_text='Isi untuk peran Staff/PIC Outlet saja (akses 1 outlet).',
    )
    city = forms.ModelChoiceField(
        label='Kota', queryset=City.objects.filter(is_active=True), required=False,
        widget=forms.Select(attrs=ADMIN_SELECT_ATTRS),
        help_text='Isi untuk peran Manager Kota atau QC/Trainer (akses semua outlet di kota itu).',
    )
    phone = forms.CharField(label='No. WhatsApp', max_length=30, required=False,
                             widget=forms.TextInput(attrs=ADMIN_TEXT_ATTRS))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')
        widgets = {'username': forms.TextInput(attrs=ADMIN_TEXT_ATTRS)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({**ADMIN_TEXT_ATTRS, 'style': 'padding-right:44px;'})
        self.fields['password2'].widget.attrs.update({**ADMIN_TEXT_ATTRS, 'style': 'padding-right:44px;'})

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            user.is_staff = True
            user.save(update_fields=['is_staff'])
            StaffProfile.objects.update_or_create(
                user=user,
                defaults={
                    'role': self.cleaned_data['role'],
                    'branch': self.cleaned_data.get('branch'),
                    'city': self.cleaned_data.get('city'),
                    'phone': self.cleaned_data.get('phone', ''),
                },
            )
        return user


class StaffAccountEditForm(forms.ModelForm):
    """Form mengubah akun yang sudah ada: data user, peran, cakupan akses, dan opsional ganti password."""
    role = forms.ChoiceField(label='Peran', choices=StaffProfile.Role.choices, widget=forms.Select(attrs=ADMIN_SELECT_ATTRS))
    branch = forms.ModelChoiceField(
        label='Outlet', queryset=Branch.objects.filter(is_active=True), required=False,
        widget=forms.Select(attrs=ADMIN_SELECT_ATTRS),
        help_text='Isi untuk peran Staff/PIC Outlet saja (akses 1 outlet).',
    )
    city = forms.ModelChoiceField(
        label='Kota', queryset=City.objects.filter(is_active=True), required=False,
        widget=forms.Select(attrs=ADMIN_SELECT_ATTRS),
        help_text='Isi untuk peran Manager Kota atau QC/Trainer (akses semua outlet di kota itu).',
    )
    phone = forms.CharField(label='No. WhatsApp', max_length=30, required=False,
                             widget=forms.TextInput(attrs=ADMIN_TEXT_ATTRS))
    new_password = forms.CharField(
        label='Password Baru', required=False,
        widget=forms.PasswordInput(attrs={**ADMIN_TEXT_ATTRS, 'style': 'padding-right:44px;'}),
        help_text='Kosongkan jika tidak ingin mengubah password.',
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'is_active')
        widgets = {
            'username': forms.TextInput(attrs=ADMIN_TEXT_ATTRS),
            'first_name': forms.TextInput(attrs=ADMIN_TEXT_ATTRS),
            'last_name': forms.TextInput(attrs=ADMIN_TEXT_ATTRS),
            'email': forms.EmailInput(attrs=ADMIN_TEXT_ATTRS),
        }
        labels = {
            'username': 'Username', 'first_name': 'Nama Depan', 'last_name': 'Nama Belakang',
            'email': 'Email', 'is_active': 'Akun Aktif',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        profile = getattr(self.instance, 'staff_profile', None)
        if profile is not None:
            self.fields['role'].initial = profile.role
            self.fields['branch'].initial = profile.branch_id
            self.fields['city'].initial = profile.city_id
            self.fields['phone'].initial = profile.phone

    def save(self, commit=True):
        user = super().save(commit=commit)
        new_password = self.cleaned_data.get('new_password')
        if commit:
            if new_password:
                user.set_password(new_password)
                user.save(update_fields=['password'])
            StaffProfile.objects.update_or_create(
                user=user,
                defaults={
                    'role': self.cleaned_data['role'],
                    'branch': self.cleaned_data.get('branch'),
                    'city': self.cleaned_data.get('city'),
                    'phone': self.cleaned_data.get('phone', ''),
                },
            )
        return user


class CityAdminForm(forms.ModelForm):
    """Form tambah/ubah kota. HANYA Admin Pusat yang berhak (dibatasi di views.py)."""

    class Meta:
        model = City
        fields = ['name', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={**ADMIN_TEXT_ATTRS, 'placeholder': 'Contoh: Jakarta'}),
        }
        labels = {'is_active': 'Kota Aktif'}


class BranchAdminForm(forms.ModelForm):
    """Form tambah/ubah outlet, untuk Admin Pusat."""

    class Meta:
        model = Branch
        fields = ['name', 'code', 'address', 'city', 'phone', 'manager', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs=ADMIN_TEXT_ATTRS),
            'code': forms.TextInput(attrs={**ADMIN_TEXT_ATTRS, 'placeholder': 'Contoh: JKT-02'}),
            'address': forms.Textarea(attrs={**ADMIN_TEXT_ATTRS, 'rows': 2}),
            'city': forms.Select(attrs=ADMIN_SELECT_ATTRS),
            'phone': forms.TextInput(attrs=ADMIN_TEXT_ATTRS),
            'manager': forms.Select(attrs=ADMIN_SELECT_ATTRS),
        }
        labels = {'is_active': 'Outlet Aktif'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['city'].queryset = City.objects.filter(is_active=True)
        self.fields['city'].required = False
        self.fields['city'].empty_label = '-- Pilih Kota --'
        self.fields['manager'].queryset = User.objects.filter(staff_profile__role=StaffProfile.Role.MANAGER)
        self.fields['manager'].required = False


class SiteSettingsForm(forms.ModelForm):
    """Form mengubah nama perusahaan & logo."""

    class Meta:
        model = SiteSettings
        fields = ['company_name', 'logo']
        widgets = {
            'company_name': forms.TextInput(attrs={**ADMIN_TEXT_ATTRS, 'placeholder': 'Nama perusahaan/restoran Anda'}),
            'logo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
        labels = {'company_name': 'Nama Perusahaan', 'logo': 'Logo Perusahaan'}


class ComplaintSourceForm(forms.ModelForm):
    """Form tambah/ubah Sumber Komplain. HANYA Admin Pusat yang berhak."""

    class Meta:
        model = ComplaintSource
        fields = ['name', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={**ADMIN_TEXT_ATTRS, 'placeholder': 'Contoh: WhatsApp'}),
        }
        labels = {'is_active': 'Aktif'}


class ComplaintDetailItemForm(forms.ModelForm):
    """Form tambah/ubah Rincian Komplain (di bawah Komplain Produk/Servis).
    HANYA Admin Pusat yang berhak."""

    class Meta:
        model = ComplaintDetailItem
        fields = ['main_type', 'name', 'is_active']
        widgets = {
            'main_type': forms.Select(attrs=ADMIN_SELECT_ATTRS),
            'name': forms.TextInput(attrs={**ADMIN_TEXT_ATTRS, 'placeholder': 'Contoh: Kualitas Makanan'}),
        }
        labels = {'main_type': 'Jenis Komplain', 'is_active': 'Aktif'}


class StyledPasswordChangeForm(PasswordChangeForm):
    """Form ganti password, dipakai SEMUA user (bukan cuma Admin Pusat) untuk
    mengganti password mereka sendiri, dengan tampilan konsisten aplikasi."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].widget.attrs.update({'class': 'form-control', 'style': 'padding-right:44px;'})
        self.fields['new_password1'].widget.attrs.update({'class': 'form-control', 'style': 'padding-right:44px;'})
        self.fields['new_password2'].widget.attrs.update({'class': 'form-control', 'style': 'padding-right:44px;'})
        self.fields['old_password'].label = 'Password Saat Ini'
        self.fields['new_password1'].label = 'Password Baru'
        self.fields['new_password2'].label = 'Ulangi Password Baru'


class StaffPhoneEditForm(forms.ModelForm):
    """Form minimal: HANYA nomor WhatsApp. Dipakai Manager Area untuk mengubah
    nomor QC/Trainer & Leader Outlet di kotanya sendiri (tidak bisa ubah field lain)."""

    class Meta:
        model = StaffProfile
        fields = ['phone']
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '08xxxxxxxxxx'}),
        }
        labels = {'phone': 'No. WhatsApp'}
