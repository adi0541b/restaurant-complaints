"""
Django settings for restaurant_complaints project.

Aplikasi Manajemen Komplain Pelanggan - Restoran Multi-Outlet
"""

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')  # aman dipanggil walau .env tidak ada (misal di Render)

# ---------------------------------------------------------------------------
# Keamanan dasar
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-CHANGE-THIS-KEY-BEFORE-PRODUCTION-!!!'
)

DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if h.strip()
]

# Render menyediakan hostname layanan lewat env var ini secara otomatis.
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get('DJANGO_CSRF_TRUSTED_ORIGINS', '').split(',') if o.strip()
]
if RENDER_EXTERNAL_HOSTNAME:
    CSRF_TRUSTED_ORIGINS.append(f'https://{RENDER_EXTERNAL_HOSTNAME}')

# ---------------------------------------------------------------------------
# Aplikasi
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    'complaints',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'restaurant_complaints.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'complaints.context_processors.branding',
            ],
        },
    },
]

WSGI_APPLICATION = 'restaurant_complaints.wsgi.application'
ASGI_APPLICATION = 'restaurant_complaints.asgi.application'

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
# Jika environment variable DATABASE_URL tersedia (mis. dari Render Postgres),
# pakai itu. Kalau tidak, jatuh ke SQLite lokal untuk development.
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    DATABASES = {
        'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600, ssl_require=True)
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ---------------------------------------------------------------------------
# Validasi password
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ---------------------------------------------------------------------------
# Internasionalisasi (Indonesia)
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'id'
TIME_ZONE = 'Asia/Makassar'  # WITA - sesuaikan dengan zona waktu outlet Anda
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# File statis & media (upload foto bukti komplain)
# ---------------------------------------------------------------------------
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# Login / redirect
# ---------------------------------------------------------------------------
LOGIN_URL = 'complaints:login'
LOGIN_REDIRECT_URL = 'complaints:dashboard'
LOGOUT_REDIRECT_URL = 'complaints:home'

# ---------------------------------------------------------------------------
# Email (development: tampil di console). Ganti ke SMTP saat produksi.
# ---------------------------------------------------------------------------
EMAIL_BACKEND = os.environ.get(
    'DJANGO_EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend'
)
EMAIL_HOST = os.environ.get('DJANGO_EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('DJANGO_EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('DJANGO_EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('DJANGO_EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.environ.get('DJANGO_DEFAULT_FROM_EMAIL', 'noreply@restoran.example.com')

# ---------------------------------------------------------------------------
# WhatsApp notification (stub - isi dengan kredensial provider Anda,
# misalnya Twilio, Fonnte, atau WhatsApp Business Cloud API)
# ---------------------------------------------------------------------------
WHATSAPP_API_URL = os.environ.get('WHATSAPP_API_URL', '')
WHATSAPP_API_TOKEN = os.environ.get('WHATSAPP_API_TOKEN', '')
WHATSAPP_NOTIFICATIONS_ENABLED = os.environ.get('WHATSAPP_NOTIFICATIONS_ENABLED', 'False') == 'True'

# ---------------------------------------------------------------------------
# Pengaturan SLA (dalam jam) berdasarkan tingkat keparahan komplain
# ---------------------------------------------------------------------------
SLA_HOURS = {
    'kritis': 4,     # Kritis: keracunan makanan, benda asing, dsb -> respons 4 jam
    'tinggi': 12,     # Tinggi: pelayanan buruk, kesalahan pesanan besar
    'sedang': 24,     # Sedang: makanan kurang matang/dingin, dsb
    'rendah': 72,     # Rendah: saran, masukan minor
}

# Batas ukuran upload foto bukti (5 MB)
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

# Nama & identitas brand (dipakai di context_processor; nama & logo aktual
# sebenarnya disimpan di model SiteSettings dan diatur lewat Panel Admin)
RESTAURANT_BRAND_NAME = os.environ.get('RESTAURANT_BRAND_NAME', 'Rasa Nusantara')
BRAND_COLOR_PRIMARY = '#7A1F1F'   # Maroon
BRAND_COLOR_ACCENT = '#C9A227'    # Gold

# ---------------------------------------------------------------------------
# Keamanan tambahan saat produksi (otomatis aktif kalau DEBUG=False)
# ---------------------------------------------------------------------------
if not DEBUG:
    SECURE_SSL_REDIRECT = os.environ.get('DJANGO_SECURE_SSL_REDIRECT', 'True') == 'True'
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
