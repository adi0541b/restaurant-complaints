from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Branch, City, Complaint, SiteSettings, StaffProfile

User = get_user_model()


class ComplaintSubmissionForm(forms.ModelForm):
    """Form pengajuan komplain oleh pelanggan (halaman publik, tanpa login)."""

    class Meta:
        model = Complaint
        fields = [
            'customer_name', 'customer_phone', 'customer_email',
            'branch', 'visit_date', 'order_number',
            'category', 'severity', 'description', 'photo_evidence',
        ]
        widgets = {
            'customer_name': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Nama lengkap Anda'}),
            'customer_phone': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': '08xxxxxxxxxx'}),
            'customer_email': forms.EmailInput(attrs={
                'class': 'form-control', 'placeholder': 'email@contoh.com (opsional)'}),
            'branch': forms.Select(attrs={'class': 'form-select'}),
            'visit_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'order_number': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Nomor struk/pesanan (opsional)'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'severity': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 5,
                'placeholder': 'Ceritakan detail komplain Anda...'}),
            'photo_evidence': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'customer_name': 'Nama Anda',
            'customer_phone': 'No. HP / WhatsApp',
            'severity': 'Tingkat Keparahan (menurut Anda)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['branch'].queryset = Branch.objects.filter(is_active=True)
        self.fields['customer_email'].required = False
        self.fields['order_number'].required = False
        self.fields['visit_date'].required = False
        self.fields['photo_evidence'].required = False


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
    (visibilitas bertahap, 2 gerbang konfirmasi Validator):

    - Status & Tingkat Keparahan : hanya Staff Input Komplain
    - Akar Masalah               : hanya Staff/PIC Cabang
    - Solusi                     : hanya Staff/PIC Cabang, MUNCUL setelah
                                    Akar Masalah terisi
    - [Gerbang 1] Solusi Dikonfirmasi Validator : hanya Validator, MUNCUL
                                    setelah Solusi terisi
    - Validasi (teks)            : hanya Staff/PIC Cabang, MUNCUL setelah
                                    Gerbang 1 dicentang Validator
    - [Gerbang 2] Dikonfirmasi Validator : hanya Validator, MUNCUL setelah
                                    Validasi (teks) terisi -> status Selesai
    """

    class Meta:
        model = Complaint
        fields = [
            'status', 'severity', 'resolution_notes', 'internal_notes',
            'solution_confirmed', 'validation_notes', 'validated',
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
            'solution_confirmed': forms.CheckboxInput(),
            'validation_notes': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Catatan validasi (bukti/verifikasi bahwa solusi sudah diterapkan)'}),
            'validated': forms.CheckboxInput(),
        }
        labels = {
            'resolution_notes': 'Akar Masalah',
            'internal_notes': 'Solusi',
            'solution_confirmed': 'Centang: Solusi sudah benar (mengizinkan Staff mengisi Validasi)',
            'validation_notes': 'Validasi',
            'validated': 'Centang: Validasi sudah benar (menyelesaikan komplain)',
        }

    def __init__(self, *args, **kwargs):
        profile = kwargs.pop('profile', None)
        super().__init__(*args, **kwargs)

        sudah_dikonfirmasi = bool(self.instance and self.instance.validated)

        # Status & Tingkat Keparahan: hanya Staff Input Komplain
        if not (profile and profile.is_input_staff):
            del self.fields['status']
            del self.fields['severity']

        # Akar Masalah: hanya Staff/PIC Cabang, DAN hanya selama belum dikonfirmasi
        if not (profile and profile.is_staff_pic) or sudah_dikonfirmasi:
            if 'resolution_notes' in self.fields:
                del self.fields['resolution_notes']

        # Solusi: hanya Staff/PIC Cabang, muncul setelah Akar Masalah terisi,
        # DAN hanya selama belum dikonfirmasi
        akar_masalah_sudah_terisi = bool(self.instance and self.instance.resolution_notes)
        if 'internal_notes' in self.fields:
            if not (profile and profile.is_staff_pic) or not akar_masalah_sudah_terisi or sudah_dikonfirmasi:
                del self.fields['internal_notes']

        # [Gerbang 1] Solusi Dikonfirmasi Validator: hanya Validator,
        # muncul setelah Solusi terisi
        solusi_sudah_terisi = bool(self.instance and self.instance.internal_notes)
        if 'solution_confirmed' in self.fields:
            if not (profile and profile.is_validator) or not solusi_sudah_terisi:
                del self.fields['solution_confirmed']
            elif self.instance.solution_confirmed:
                self.fields['solution_confirmed'].disabled = True

        # Validasi (teks): hanya Staff/PIC Cabang, muncul setelah Gerbang 1
        # dicentang Validator, DAN hanya selama belum dikonfirmasi akhir
        gerbang1_sudah_dicentang = bool(self.instance and self.instance.solution_confirmed)
        if 'validation_notes' in self.fields:
            if not (profile and profile.is_staff_pic) or not gerbang1_sudah_dicentang or sudah_dikonfirmasi:
                del self.fields['validation_notes']

        # [Gerbang 2] Dikonfirmasi Validator: hanya Validator, muncul setelah
        # Validasi (teks) terisi
        validasi_teks_sudah_terisi = bool(self.instance and self.instance.validation_notes)
        if 'validated' in self.fields:
            if not (profile and profile.is_validator) or not validasi_teks_sudah_terisi:
                del self.fields['validated']
            elif sudah_dikonfirmasi:
                self.fields['validated'].disabled = True
            elif self.instance.validated:
                # Sudah pernah divalidasi -> kunci checkbox (tidak bisa dibatalkan lewat form)
                self.fields['validated'].disabled = True


# =============================================================================
# PANEL ADMIN PUSAT: kelola akun staff, cabang, dan identitas perusahaan
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
        label='Cabang', queryset=Branch.objects.filter(is_active=True), required=False,
        widget=forms.Select(attrs=ADMIN_SELECT_ATTRS),
        help_text='Isi untuk peran Staff/PIC Cabang saja (akses 1 cabang).',
    )
    city = forms.ModelChoiceField(
        label='Kota', queryset=City.objects.filter(is_active=True), required=False,
        widget=forms.Select(attrs=ADMIN_SELECT_ATTRS),
        help_text='Isi untuk peran Manager Kota saja (akses semua cabang di kota itu).',
    )
    phone = forms.CharField(label='No. WhatsApp', max_length=30, required=False,
                             widget=forms.TextInput(attrs=ADMIN_TEXT_ATTRS))

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')
        widgets = {'username': forms.TextInput(attrs=ADMIN_TEXT_ATTRS)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update(ADMIN_TEXT_ATTRS)
        self.fields['password2'].widget.attrs.update(ADMIN_TEXT_ATTRS)

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
        label='Cabang', queryset=Branch.objects.filter(is_active=True), required=False,
        widget=forms.Select(attrs=ADMIN_SELECT_ATTRS),
        help_text='Isi untuk peran Staff/PIC Cabang saja (akses 1 cabang).',
    )
    city = forms.ModelChoiceField(
        label='Kota', queryset=City.objects.filter(is_active=True), required=False,
        widget=forms.Select(attrs=ADMIN_SELECT_ATTRS),
        help_text='Isi untuk peran Manager Kota saja (akses semua cabang di kota itu).',
    )
    phone = forms.CharField(label='No. WhatsApp', max_length=30, required=False,
                             widget=forms.TextInput(attrs=ADMIN_TEXT_ATTRS))
    new_password = forms.CharField(
        label='Password Baru', required=False, widget=forms.PasswordInput(attrs=ADMIN_TEXT_ATTRS),
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
    """Form tambah/ubah cabang, untuk Admin Pusat."""

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
        labels = {'is_active': 'Cabang Aktif'}

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
