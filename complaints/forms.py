from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Branch, Complaint, SiteSettings, StaffProfile

User = get_user_model()


class ComplaintSubmissionForm(forms.ModelForm):
    """Form pengajuan komplain oleh pelanggan (halaman publik, tanpa login)."""

    class Meta:
        model = Complaint
        fields = [
            'customer_name', 'customer_phone', 'customer_email',
            'branch', 'table_number', 'visit_date', 'order_number',
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
            'table_number': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Contoh: A12 (opsional)'}),
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
        self.fields['table_number'].required = False
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
    """Form untuk Staff/Manager memperbarui status & penanganan komplain."""

    class Meta:
        model = Complaint
        fields = [
            'status', 'assigned_to', 'severity',
            'resolution_notes', 'internal_notes',
        ]
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'severity': forms.Select(attrs={'class': 'form-select'}),
            'resolution_notes': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Tindakan/solusi yang diberikan ke pelanggan'}),
            'internal_notes': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Catatan internal, tidak terlihat oleh pelanggan'}),
        }

    def __init__(self, *args, **kwargs):
        branch = kwargs.pop('branch', None)
        super().__init__(*args, **kwargs)
        if branch is not None:
            self.fields['assigned_to'].queryset = User.objects.filter(
                staff_profile__branch=branch
            )


# =============================================================================
# PANEL ADMIN PUSAT: kelola akun staff, cabang, dan identitas perusahaan
# =============================================================================
ADMIN_TEXT_ATTRS = {'class': 'form-control'}
ADMIN_SELECT_ATTRS = {'class': 'form-select'}


class StaffAccountCreateForm(UserCreationForm):
    """Form membuat akun baru (Staff/PIC, Manager, atau Admin Pusat)."""
    first_name = forms.CharField(label='Nama Depan', max_length=150, widget=forms.TextInput(attrs=ADMIN_TEXT_ATTRS))
    last_name = forms.CharField(label='Nama Belakang', max_length=150, required=False,
                                 widget=forms.TextInput(attrs=ADMIN_TEXT_ATTRS))
    email = forms.EmailField(label='Email', required=False, widget=forms.EmailInput(attrs=ADMIN_TEXT_ATTRS))
    role = forms.ChoiceField(label='Peran', choices=StaffProfile.Role.choices, widget=forms.Select(attrs=ADMIN_SELECT_ATTRS))
    branch = forms.ModelChoiceField(
        label='Cabang', queryset=Branch.objects.filter(is_active=True), required=False,
        widget=forms.Select(attrs=ADMIN_SELECT_ATTRS),
        help_text='Kosongkan untuk peran Admin Pusat (akses semua cabang).',
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
                    'phone': self.cleaned_data.get('phone', ''),
                },
            )
        return user


class StaffAccountEditForm(forms.ModelForm):
    """Form mengubah akun yang sudah ada: data user, peran, cabang, dan opsional ganti password."""
    role = forms.ChoiceField(label='Peran', choices=StaffProfile.Role.choices, widget=forms.Select(attrs=ADMIN_SELECT_ATTRS))
    branch = forms.ModelChoiceField(
        label='Cabang', queryset=Branch.objects.filter(is_active=True), required=False,
        widget=forms.Select(attrs=ADMIN_SELECT_ATTRS),
        help_text='Kosongkan untuk peran Admin Pusat (akses semua cabang).',
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
                    'phone': self.cleaned_data.get('phone', ''),
                },
            )
        return user


class BranchAdminForm(forms.ModelForm):
    """Form tambah/ubah cabang, untuk Admin Pusat."""

    class Meta:
        model = Branch
        fields = ['name', 'code', 'address', 'city', 'phone', 'manager', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs=ADMIN_TEXT_ATTRS),
            'code': forms.TextInput(attrs={**ADMIN_TEXT_ATTRS, 'placeholder': 'Contoh: JKT-02'}),
            'address': forms.Textarea(attrs={**ADMIN_TEXT_ATTRS, 'rows': 2}),
            'city': forms.TextInput(attrs=ADMIN_TEXT_ATTRS),
            'phone': forms.TextInput(attrs=ADMIN_TEXT_ATTRS),
            'manager': forms.Select(attrs=ADMIN_SELECT_ATTRS),
        }
        labels = {'is_active': 'Cabang Aktif'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
