# Aplikasi Manajemen Komplain Pelanggan Restoran (Django)

Aplikasi web untuk mengelola komplain pelanggan restoran multi-cabang, dengan
4 peran pengguna: **Pelanggan**, **Staff/PIC**, **Manager**, dan **Admin Pusat**.

## Fitur Utama

- Form pengajuan komplain publik (tanpa login), mendukung **prefill lewat QR/URL**
  contoh: `http://domain.com/?cabang=JKT-01&meja=A12`
- Kode komplain otomatis (`CMP-00001`, `CMP-00002`, ...) untuk keterlacakan
- **SLA otomatis** dihitung sesuai tingkat keparahan (Kritis/Tinggi/Sedang/Rendah),
  dengan deteksi keterlambatan (overdue) - lihat `SLA_HOURS` di `settings.py`
- Cek status komplain mandiri oleh pelanggan (kode + no. HP)
- Rating kepuasan pelanggan setelah komplain selesai
- Dashboard ringkasan untuk Staff/Manager/Admin Pusat (total, per kategori, per cabang, overdue)
- Riwayat/timeline perubahan status tiap komplain
- Notifikasi **email** otomatis (development: tampil di console) dan stub **WhatsApp**
  (siap diisi provider seperti Fonnte/Twilio/WhatsApp Business Cloud API)
- Django Admin lengkap dengan badge warna status & tingkat keparahan
- Tema warna **maroon (#7A1F1F) & gold (#C9A227)** konsisten di seluruh halaman

## Struktur Peran (StaffProfile)

| Peran | Akses |
|---|---|
| Pelanggan | Tidak perlu login: ajukan komplain, cek status, beri rating |
| Staff / PIC | Login, lihat & tangani komplain cabangnya sendiri |
| Manager | Login, sama seperti Staff namun untuk pengawasan cabang |
| Admin Pusat | Login, akses semua cabang, kelola data master via Django Admin |

## Instalasi & Menjalankan di Komputer Anda

### 1. Prasyarat
- Python 3.10 atau lebih baru
- pip

### 2. Setup environment

```bash
cd restaurant_complaints

# buat virtual environment
python -m venv venv

# aktifkan (Windows)
venv\Scripts\activate
# aktifkan (Mac/Linux)
source venv/bin/activate

# install dependencies
pip install -r requirements.txt
```

### 3. Konfigurasi environment variable (opsional untuk development)

```bash
cp .env.example .env
```

Aplikasi sudah bisa jalan tanpa `.env` (memakai nilai default development).
Untuk produksi, wajib isi `.env` dengan `DJANGO_SECRET_KEY` baru dan `DEBUG=False`.
`settings.py` sudah otomatis memuat file `.env` jika ada — tidak perlu langkah tambahan.

### 4. Migrasi database

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Buat akun superuser (opsional, untuk akses penuh Django Admin)

```bash
python manage.py createsuperuser
```

### 6. Isi data contoh (cabang, staff, dan contoh komplain)

```bash
python manage.py seed_demo_data --complaints 25
```

Perintah ini akan membuat:
- 3 cabang contoh (Jakarta, Bandung, Semarang)
- 1 akun Admin Pusat: `adminpusat` / `admin12345`
- 3 akun Manager: `manager1`, `manager2`, `manager3` / `manager12345`
- 3 akun Staff: `staff1`, `staff2`, `staff3` / `staff12345`
- 25 contoh komplain dengan variasi status, tingkat, dan tanggal

> **Penting:** Ganti semua password di atas sebelum digunakan di lingkungan produksi.

### 7. Jalankan server development

```bash
python manage.py runserver
```

Buka di browser:
- **Form komplain publik:** http://127.0.0.1:8000/
- **Cek status komplain:** http://127.0.0.1:8000/cek-status/
- **Login staff/manager/admin:** http://127.0.0.1:8000/login/
- **Dashboard internal:** http://127.0.0.1:8000/dashboard/
- **Django Admin:** http://127.0.0.1:8000/admin/

## Menyesuaikan SLA

Edit `SLA_HOURS` di `restaurant_complaints/settings.py`:

```python
SLA_HOURS = {
    'kritis': 4,
    'tinggi': 12,
    'sedang': 24,
    'rendah': 72,
}
```

## Mengaktifkan Notifikasi WhatsApp

1. Daftar ke provider WhatsApp API pilihan Anda (Fonnte, Twilio, WhatsApp Business Cloud API, dll).
2. Isi `.env`:
   ```
   WHATSAPP_NOTIFICATIONS_ENABLED=True
   WHATSAPP_API_URL=https://url-endpoint-provider-anda
   WHATSAPP_API_TOKEN=token-anda
   ```
3. Sesuaikan format request pada fungsi `send_whatsapp_notification` di
   `complaints/signals.py` sesuai dokumentasi provider yang dipakai (payload
   `requests.post` saat ini adalah contoh generik).

## Mengaktifkan Email Produksi (SMTP)

Isi `.env`:
```
DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
DJANGO_EMAIL_HOST=smtp.gmail.com
DJANGO_EMAIL_HOST_USER=email-anda@gmail.com
DJANGO_EMAIL_HOST_PASSWORD=app-password-anda
```

## QR Code per Meja

Buat QR code yang mengarah ke:
```
https://domain-anda.com/?cabang=<KODE_CABANG>&meja=<NOMOR_MEJA>
```
Contoh: `https://domain-anda.com/?cabang=JKT-01&meja=A12`

Form pengajuan komplain akan otomatis mengisi cabang & nomor meja pelanggan.

## Deploy ke Render

Render men-deploy dari repository Git (GitHub/GitLab), bukan dari upload zip
langsung. Jadi langkah pertama adalah mengunggah project ini ke GitHub.

### 1. Unggah project ke GitHub

```bash
cd restaurant_complaints
git init
git add .
git commit -m "Initial commit - aplikasi komplain restoran"
```

Buat repository baru (kosong) di https://github.com/new, lalu:

```bash
git branch -M main
git remote add origin https://github.com/USERNAME-ANDA/restaurant-complaints.git
git push -u origin main
```

> File `db.sqlite3`, `media/`, `.env`, dan `venv/` sudah otomatis diabaikan
> lewat `.gitignore` — jangan unggah data sensitif/lokal ke GitHub.

### 2. Buat akun & Web Service di Render

1. Daftar/login di https://render.com (bisa langsung pakai akun GitHub).
2. Klik **New +** → **Web Service**.
3. Pilih repository `restaurant-complaints` yang baru Anda push.
4. Isi konfigurasi:
   - **Name**: bebas, misalnya `restaurant-complaints`
   - **Region**: pilih yang terdekat (mis. Singapore)
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `./build.sh`
   - **Start Command**: `gunicorn restaurant_complaints.wsgi:application`
   - **Plan**: `Free` (cukup untuk uji coba; ada batasan sleep setelah idle)

> **Alternatif lebih cepat:** jika repository sudah berisi file `render.yaml`
> (sudah disertakan di project ini), Anda bisa memakai **New +** → **Blueprint**
> lalu arahkan ke repo tersebut — Render akan otomatis membuatkan Web Service
> **dan** database PostgreSQL sekaligus, tanpa perlu isi form manual di atas.

### 3. Tambahkan database PostgreSQL (jika tidak pakai Blueprint)

SQLite tidak cocok untuk Render karena disknya bersifat sementara (data hilang
setiap deploy ulang). Buat database terpisah:

1. **New +** → **PostgreSQL**, beri nama bebas, plan **Free**.
2. Setelah database dibuat, salin nilai **Internal Database URL**.
3. Kembali ke Web Service Anda → tab **Environment** → tambahkan variabel
   `DATABASE_URL` dengan nilai yang disalin tadi.

### 4. Isi Environment Variables di Web Service

Buka tab **Environment** pada Web Service, tambahkan minimal:

| Key | Value |
|---|---|
| `DJANGO_SECRET_KEY` | isi string acak yang panjang (klik "Generate" di Render) |
| `DJANGO_DEBUG` | `False` |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` (nama domain Render ditambahkan otomatis oleh aplikasi) |
| `RESTAURANT_BRAND_NAME` | nama restoran Anda |
| `PYTHON_VERSION` | `3.12.4` (atau versi Python 3.10–3.13 pilihan Anda) |
| `DATABASE_URL` | (dari langkah 3, jika tidak pakai Blueprint) |

Variabel email/WhatsApp bersifat opsional, isi jika ingin fitur itu aktif di produksi (lihat bagian di bawah).

### 5. Deploy

Klik **Create Web Service** (atau **Apply** jika pakai Blueprint). Render akan
otomatis menjalankan `build.sh` (install dependencies, `collectstatic`,
`migrate`) lalu menjalankan `gunicorn`. Proses awal biasanya 2–5 menit.

Setelah selesai, aplikasi bisa diakses di URL yang diberikan Render, contoh:
`https://restaurant-complaints.onrender.com`

### 6. Buat superuser & isi data awal di Render

Buka tab **Shell** pada Web Service di dashboard Render, lalu jalankan:

```bash
python manage.py createsuperuser
python manage.py seed_demo_data --complaints 25
```

### ⚠️ Catatan penting soal file upload (foto komplain & logo)

Pada plan **Free** Render, filesystem bersifat **sementara (ephemeral)** —
artinya file yang diupload lewat aplikasi (foto bukti komplain, logo
perusahaan di Panel Admin) **akan hilang setiap kali di-deploy ulang atau
restart**. Untuk penggunaan produksi jangka panjang, salah satu opsi berikut
disarankan:

- Upgrade ke **Render Disk** (plan berbayar) untuk penyimpanan file yang persisten, atau
- Gunakan storage eksternal seperti **Amazon S3** / **Cloudflare R2** dengan
  paket `django-storages` (butuh sedikit penyesuaian `settings.py`) — beri
  tahu saya jika ingin saya bantu setup ini.

Untuk sekadar demo/uji coba, kondisi default (tanpa disk tambahan) sudah cukup.

### 7. Update aplikasi di kemudian hari

Setiap kali Anda `git push` ke branch `main`, Render otomatis mendeteksi
perubahan dan men-deploy ulang secara otomatis.

## Deploy ke Produksi (ringkas, untuk hosting lain selain Render)

1. Set `DJANGO_DEBUG=False` dan `DJANGO_ALLOWED_HOSTS` sesuai domain Anda.
2. Ganti database ke PostgreSQL/MySQL bila diperlukan (edit `DATABASES` di `settings.py`).
3. Jalankan `python manage.py collectstatic`.
4. Gunakan Gunicorn/uWSGI + Nginx, atau platform seperti Railway/Render/PythonAnywhere.
5. Aktifkan HTTPS dan set `SECURE_SSL_REDIRECT = True`, `SESSION_COOKIE_SECURE = True`, dst.

## Struktur Proyek

```
restaurant_complaints/
├── manage.py
├── requirements.txt
├── .env.example
├── restaurant_complaints/      # konfigurasi proyek
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py / asgi.py
└── complaints/                 # aplikasi utama
    ├── models.py                # Branch, StaffProfile, Complaint, Timeline
    ├── views.py                 # halaman publik & internal
    ├── forms.py
    ├── admin.py
    ├── signals.py                # notifikasi email/WhatsApp otomatis
    ├── urls.py
    ├── context_processors.py
    ├── management/commands/seed_demo_data.py
    ├── templates/complaints/     # tema maroon & gold
    └── static/complaints/css/style.css
```
