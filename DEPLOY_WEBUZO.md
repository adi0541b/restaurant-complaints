# Deploy ke Webuzo (Domain: sinergiberkahsukses.com)

Webuzo adalah panel hosting untuk **VPS/dedicated server** (mirip cPanel),
biasanya dipakai dengan akses **SSH**. Berbeda dengan Render, di sini file
Anda tersimpan permanen di server (tidak hilang saat restart), jadi SQLite
pun sebenarnya aman dipakai untuk skala kecil-menengah — tapi MySQL/MariaDB
lebih disarankan untuk beban lebih besar dan sudah tersedia bawaan di Webuzo.

## Sebelum mulai: cek dulu fitur Webuzo Anda

Buka panel Webuzo Anda dan cek di menu **Applications** / **Software** apakah
ada fitur **"Setup Python App"** atau **"Python Selector"** (mirip fitur
Passenger di cPanel). Jika ADA:
- Fitur itu akan mengurus virtualenv & reverse proxy secara otomatis — jauh
  lebih mudah dari langkah manual di bawah. Cukup arahkan "Application Root"
  ke folder project, "Startup File" ke `restaurant_complaints/wsgi.py`, lalu
  jalankan `pip install -r requirements.txt` lewat tombol yang disediakan.
- Kalau begini, Anda bisa lewati bagian **Gunicorn + systemd** di bawah, dan
  langsung ke bagian **Database** & **Environment Variables**.

Jika TIDAK ADA fitur itu (lebih umum di Webuzo versi VPS polos), ikuti
panduan manual lengkap di bawah ini (Gunicorn + systemd + Nginx).

---

## 1. Arahkan domain ke server & buat website di Webuzo

1. Di pengelola DNS domain `sinergiberkahsukses.com` Anda, buat/pastikan
   **A record** mengarah ke alamat IP server Webuzo Anda.
2. Di panel Webuzo: **Websites** → **Add Domain**, masukkan
   `sinergiberkahsukses.com`, dan buat akun/website untuk domain ini
   (catat **username sistem** yang dibuat, misalnya `sinergi`).
3. Tunggu propagasi DNS (bisa beberapa menit hingga beberapa jam).

## 2. Masuk ke server lewat SSH

```bash
ssh username_anda@sinergiberkahsukses.com
# atau ssh username_anda@ip-server-anda
```

Jika belum ada akses SSH, aktifkan dulu lewat panel Webuzo (**Websites** →
domain Anda → **SSH Access**) atau minta ke penyedia VPS Anda.

## 3. Pastikan Python 3.10+ dan venv tersedia

```bash
python3 --version
python3 -m venv --help
```

Jika belum ada / versinya terlalu lama, install lewat manajer paket server
(perintah tepatnya tergantung OS server, contoh untuk Ubuntu/Debian):

```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip -y
```

(Jika Anda tidak punya akses `sudo`, minta admin VPS/provider hosting untuk
memastikan Python 3.10+ sudah tersedia.)

## 4. Upload project ke server

Opsi termudah: lewat Git (disarankan agar mudah update di kemudian hari).

```bash
cd ~/public_html          # atau folder lain di luar public_html, lihat catatan di bawah
git clone https://github.com/USERNAME-ANDA/restaurant-complaints.git restaurant_complaints
cd restaurant_complaints
```

> **Catatan keamanan:** idealnya folder project (kecuali `staticfiles/` dan
> `media/`) TIDAK ditaruh langsung di `public_html` yang bisa diakses web
> secara langsung, karena kode Python & `.env` Anda bisa berpotensi terunduh
> orang lain jika web server salah konfigurasi. Taruh project di folder
> seperti `~/restaurant_complaints` (di luar `public_html`), lalu Nginx/Apache
> cukup diarahkan ke situ lewat konfigurasi proxy (lihat langkah 9).

Kalau tidak pakai Git, upload via **File Manager** Webuzo (unggah file zip
project ini, lalu ekstrak di server), atau pakai `scp`/SFTP dari komputer
Anda.

## 5. Buat virtual environment & install dependencies

```bash
cd ~/restaurant_complaints
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Jika Anda memilih memakai MySQL/MariaDB (langkah 6), buka
`requirements.txt`, hapus tanda pagar (`#`) di baris `mysqlclient>=2.2`,
lalu jalankan lagi `pip install -r requirements.txt`. Jika instalasi
`mysqlclient` gagal karena kurang library sistem, install dulu:

```bash
sudo apt install default-libmysqlclient-dev build-essential -y
```

## 6. Siapkan database

**Opsi A — MySQL/MariaDB (disarankan untuk produksi):**

1. Di panel Webuzo: **Databases** → **MySQL Databases**, buat database baru
   (misal `sinergi_komplain`) dan user database dengan password kuat, lalu
   berikan semua hak akses (All Privileges) user tersebut ke database itu.
2. Catat: nama database, username, password, dan host (biasanya `localhost`).

**Opsi B — tetap pakai SQLite (paling sederhana, cukup untuk skala kecil):**

Lewati langkah ini — tidak perlu setup database tambahan apa pun.

## 7. Buat file `.env` produksi

```bash
cp .env.example .env
nano .env
```

Isi minimal seperti ini:

```
DJANGO_SECRET_KEY=ganti-dengan-string-acak-panjang-dan-rahasia
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=sinergiberkahsukses.com,www.sinergiberkahsukses.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://sinergiberkahsukses.com,https://www.sinergiberkahsukses.com
RESTAURANT_BRAND_NAME=Nama Restoran Anda

# Hanya isi baris DATABASE_URL ini jika pakai Opsi A (MySQL) di langkah 6:
# format: mysql://USER:PASSWORD@localhost:3306/NAMA_DATABASE
DATABASE_URL=mysql://sinergi_user:password_anda@localhost:3306/sinergi_komplain
```

> Untuk `DJANGO_SECRET_KEY`, bisa generate string acak lewat:
> `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`

Simpan file (di `nano`: `Ctrl+O` lalu Enter, keluar dengan `Ctrl+X`).

## 8. Migrasi database, kumpulkan file statis, buat superuser

```bash
mkdir -p logs
python manage.py migrate
python manage.py collectstatic --no-input
python manage.py createsuperuser
python manage.py seed_demo_data --complaints 25   # opsional, contoh data
```

## 9. Jalankan aplikasi lewat Gunicorn (systemd)

1. Salin `deploy/restaurant-complaints.service` dari project ini menjadi
   `/etc/systemd/system/restaurant-complaints.service`, lalu **sunting**
   semua path `webuzo_user` dan `/home/webuzo_user/...` di dalamnya agar
   sesuai dengan username & lokasi folder Anda yang sebenarnya:

   ```bash
   sudo cp deploy/restaurant-complaints.service /etc/systemd/system/
   sudo nano /etc/systemd/system/restaurant-complaints.service
   ```

2. Aktifkan servicenya:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable restaurant-complaints
   sudo systemctl start restaurant-complaints
   sudo systemctl status restaurant-complaints
   ```

   Pastikan statusnya `active (running)`. Jika gagal, cek log:
   `journalctl -u restaurant-complaints -n 50 --no-pager`

## 10. Hubungkan domain ke Gunicorn lewat Nginx/Apache

Buka `deploy/nginx_restaurant_complaints.conf` dari project ini sebagai
contoh, sesuaikan domain & path-nya, lalu terapkan sesuai web server yang
dipakai Webuzo Anda:

- **Jika Webuzo memakai Nginx** dan ada kolom "Custom Nginx Directives" di
  pengaturan domain: tempelkan isi blok `location /`, `location /static/`,
  dan `location /media/` ke kolom tersebut, lalu simpan (Webuzo akan reload
  Nginx otomatis).
- **Jika Anda punya akses root penuh**: salin file itu ke folder konfigurasi
  vhost Nginx untuk domain ini (biasanya di `/etc/nginx/conf.d/` atau folder
  khusus Webuzo), lalu:
  ```bash
  sudo nginx -t && sudo systemctl reload nginx
  ```
- **Jika Webuzo memakai Apache** (bukan Nginx): gunakan `ProxyPass` sebagai
  gantinya. Tambahkan ke konfigurasi VirtualHost domain Anda:
  ```apache
  ProxyPreserveHost On
  ProxyPass /static/ !
  ProxyPass /media/ !
  ProxyPass / http://127.0.0.1:8001/
  ProxyPassReverse / http://127.0.0.1:8001/
  Alias /static/ /home/webuzo_user/restaurant_complaints/staticfiles/
  Alias /media/ /home/webuzo_user/restaurant_complaints/media/
  ```
  (Modul `mod_proxy` dan `mod_proxy_http` harus aktif di Apache.)

## 11. Aktifkan SSL (HTTPS)

Di panel Webuzo: **Websites** → domain Anda → **SSL** → aktifkan
**Let's Encrypt / AutoSSL** (biasanya gratis & satu klik). Setelah aktif,
pastikan `DJANGO_CSRF_TRUSTED_ORIGINS` di `.env` sudah memakai `https://`
seperti contoh langkah 7, lalu restart aplikasi:

```bash
sudo systemctl restart restaurant-complaints
```

## 12. Uji coba

Buka `https://sinergiberkahsukses.com` di browser. Coba juga:
- `https://sinergiberkahsukses.com/login/` (login staff)
- `https://sinergiberkahsukses.com/admin/` (Django Admin, pakai akun superuser)

## Update aplikasi di kemudian hari

```bash
cd ~/restaurant_complaints
git pull
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --no-input
sudo systemctl restart restaurant-complaints
```

## Catatan izin file untuk folder `media/`

Pastikan folder `media/` (tempat foto komplain & logo perusahaan disimpan)
bisa ditulis oleh user yang menjalankan Gunicorn:

```bash
mkdir -p media
chmod -R 755 media
```

## Troubleshooting singkat

| Gejala | Kemungkinan penyebab |
|---|---|
| 502 Bad Gateway | Gunicorn belum jalan — cek `systemctl status restaurant-complaints` |
| CSS/gambar tidak muncul | `collectstatic` belum dijalankan, atau path `alias` di Nginx salah |
| `DisallowedHost` error | `DJANGO_ALLOWED_HOSTS` di `.env` belum memuat domain Anda |
| Error CSRF saat login | `DJANGO_CSRF_TRUSTED_ORIGINS` belum diisi/salah format |
| Upload foto gagal | Izin folder `media/` kurang, atau `client_max_body_size` di Nginx terlalu kecil |
