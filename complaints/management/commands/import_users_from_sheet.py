"""
Command sekali-pakai untuk:
1. Menghapus SEMUA user KECUALI 'adminpusat'.
2. Membuat ulang data Kota, Outlet (Branch), dan akun user (Leader Outlet,
   QC/Trainer, Manager Area) sesuai data dari Google Sheets yang diberikan.

Jalankan dengan:
    python manage.py import_users_from_sheet

Tambahkan --dry-run untuk melihat apa yang AKAN dilakukan tanpa benar-benar
mengubah database:
    python manage.py import_users_from_sheet --dry-run
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from complaints.models import Branch, City, StaffProfile

User = get_user_model()

# =============================================================================
# DATA DARI GOOGLE SHEETS (3 tab: LEADER OUTLET, QC/TRAINER, MANAGER AREA)
# =============================================================================

# (ID, OUTLET, KOTA, USERNAME, PASSWORD)
LEADER_OUTLET_DATA = [
    (1, 'MAS ADE', 'BALIKPAPAN', 'loade', 'abc12345'),
    (2, 'MAS ANTO', 'BALIKPAPAN', 'loanto', 'abc12345'),
    (3, 'MAS EVAN', 'BALIKPAPAN', 'loevan', 'abc12345'),
    (4, 'MAS INDRA', 'BALIKPAPAN', 'loindra', 'abc12345'),
    (5, 'MAS JOKO', 'BALIKPAPAN', 'lojoko', 'abc12345'),
    (6, 'MAS JOYO', 'BALIKPAPAN', 'lojoyo', 'abc12345'),
    (7, 'PAK JI', 'BALIKPAPAN', 'lopakji', 'abc12345'),
    (8, 'Pak Karno', 'BALIKPAPAN', 'lokarno', 'abc12345'),
    (9, 'Ayam Geprek Banua', 'BANJARMASIN', 'loagb', 'abc12345'),
    (10, 'Bubur Ayam Samarinda & Ayam Ganje', 'BANJARMASIN', 'lobasage', 'abc12345'),
    (11, 'Haji Iyan Sekumpul', 'BANJARMASIN', 'loiyan', 'abc12345'),
    (12, 'Mas Abi', 'BANJARMASIN', 'loabi', 'abc12345'),
    (13, 'Mas Afid', 'BANJARMASIN', 'loafid', 'abc12345'),
    (14, 'Mas Apapin', 'BANJARMASIN', 'loapapin', 'abc12345'),
    (15, 'Mas Bimo', 'BANJARMASIN', 'lobimo', 'abc12345'),
    (16, 'Mas Gun Kp Melayu', 'BANJARMASIN', 'logunmly', 'abc12345'),
    (17, 'Mas Gun Pramuka', 'BANJARMASIN', 'logunprmk', 'abc12345'),
    (18, 'Mas Hadi', 'BANJARMASIN', 'lohadi', 'abc12345'),
    (19, 'Mas Jono', 'BANJARMASIN', 'lojono', 'abc12345'),
    (20, 'Mas Panji', 'BANJARMASIN', 'lopanji', 'abc12345'),
    (21, 'Mbak Kayla', 'BANJARMASIN', 'lokayla', 'abc12345'),
    (22, 'Mbak Zahra', 'BANJARMASIN', 'lozahra', 'abc12345'),
    (23, 'Pak Soleh', 'BANJARMASIN', 'losoleh', 'abc12345'),
    (24, 'ABS JAKAL', 'JOGJA', 'lojakal', 'abc12345'),
    (25, 'ABS Kusumanegara', 'JOGJA', 'Lojogja', 'abc12345'),
    (26, 'Mas Sigit 1', 'MAKASSAR', 'losigit1', 'abc12345'),
    (27, 'Mas Sigit 3', 'MAKASSAR', 'losigit3', 'abc12345'),
    (28, 'Mba Ayu', 'MAKASSAR', 'loayu', 'abc12345'),
    (29, 'Mas Eko', 'PALANGKARAYA', 'loeko1', 'abc12345'),
    (30, 'Mas Eko 2', 'PALANGKARAYA', 'loeko2', 'abc12345'),
    (31, 'Mas Eko 3', 'PALANGKARAYA', 'loeko3', 'abc12345'),
    (32, 'Mas Eko 4', 'PALANGKARAYA', 'loeko4', 'abc12345'),
    (33, 'Mas Eko 5', 'PALANGKARAYA', 'loeko5', 'abc12345'),
    (34, 'Mas Eko 6', 'PALANGKARAYA', 'loeko6', 'abc12345'),
    (35, 'Mas Eko 7', 'PALANGKARAYA', 'loeko7', 'abc12345'),
    (36, 'Mas Eko 8', 'PALANGKARAYA', 'loeko8', 'abc12345'),
    (37, 'Mas Eko 9', 'PALANGKARAYA', 'loeko9', 'abc12345'),
    (38, 'Mas Bowo', 'PONTIANAK', 'lobowo', 'abc12345'),
    (39, 'Mas Teguh', 'PONTIANAK', 'loteguh', 'abc12345'),
    (40, 'Pak Edi', 'PONTIANAK', 'loedi', 'abc12345'),
    (41, 'Pak Tono', 'PONTIANAK', 'lotomo', 'abc12345'),
    (42, 'Bebek 1000 Rempah Sultan Lalapan', 'SAMARINDA', 'losulap4', 'abc12345'),
    (43, 'Bubur Ayam Kanton Asgara', 'SAMARINDA', 'lokanton', 'abc12345'),
    (44, 'EKA BANTEN', 'SAMARINDA', 'loeka', 'abc12345'),
    (45, 'Foodies', 'SAMARINDA', 'lofoodies', 'abc12345'),
    (46, 'HAJI IJAY', 'SAMARINDA', 'loijay', 'abc12345'),
    (47, 'MAS ADI', 'SAMARINDA', 'loadi', 'abc12345'),
    (48, 'MAS AGUS', 'SAMARINDA', 'loagus', 'abc12345'),
    (49, 'Mas Budi', 'SAMARINDA', 'lobudi', 'abc12345'),
    (50, 'Mas Harun', 'SAMARINDA', 'loharun', 'abc12345'),
    (51, 'Mas Karyo', 'SAMARINDA', 'lokaryo', 'abc12345'),
    (52, 'Mas Untung', 'SAMARINDA', 'lountung', 'abc12345'),
    (53, 'MAS YOGA', 'SAMARINDA', 'loyoga', 'abc12345'),
    (54, 'Mas Yono', 'SAMARINDA', 'loyono', 'abc12345'),
    (55, 'Sultan Lalapan Flores', 'SAMARINDA', 'losulap2', 'abc12345'),
    (56, 'Sultan Lalapan Lodho', 'SAMARINDA', 'losulap3', 'abc12345'),
    (57, 'Warung Makmur', 'SAMARINDA', 'lomakmur', 'abc12345'),
    (58, 'ABS Solo', 'SOLO', 'losolo', 'abc12345'),
]

# (KOTA, USERNAME, PASSWORD, NOMOR_WHATSAPP)
QC_TRAINER_DATA = [
    ('SAMARINDA', 'QCSMD', 'smd12345', '089690396830'),
    ('BALIKPAPAN', 'QCBPP', 'bpp12345', '083896432265'),
    ('BANJARMASIN', 'QCBJM', 'bjm12345', '089531474156'),
    ('PALANGKARAYA', 'QCPKY', 'pky12345', '082321807849'),
    ('SAMARINDA', 'TRNSMD', 'smd12345', '081350667491'),
    ('BALIKPAPAN', 'TRNBPP', 'bpp12345', '085750230759'),
    ('BANJARMASIN', 'TRNBJM', 'bjm12345', '08971863902'),
    ('PALANGKARAYA', 'TRNPKY', 'pky12345', '08981383173'),
]

# (KOTA, USERNAME, PASSWORD)
MANAGER_AREA_DATA = [
    ('SAMARINDA', 'MASMD', 'smd12345'),
    ('BALIKPAPAN', 'MABPP', 'bpp12345'),
    ('BANJARMASIN', 'MABJM', 'bjm12345'),
    ('MAKASSAR', 'MAMKS', 'mks12345'),
    ('PALANGKARAYA', 'MAPKY', 'pky12345'),
    ('PONTIANAK', 'MAPTK', 'ptk12345'),
    ('JOGJA', 'MAJOG', 'jog12345'),
    ('SOLO', 'MASOL', 'sol12345'),
]

# Kode singkat kota, dipakai untuk membuat kode Outlet otomatis (mis. SMD-01)
CITY_CODE_PREFIX = {
    'BALIKPAPAN': 'BPP',
    'BANJARMASIN': 'BJM',
    'JOGJA': 'JOG',
    'MAKASSAR': 'MKS',
    'PALANGKARAYA': 'PKY',
    'PONTIANAK': 'PTK',
    'SAMARINDA': 'SMD',
    'SOLO': 'SOL',
}


class Command(BaseCommand):
    help = 'Hapus semua user kecuali adminpusat, lalu impor ulang Kota/Outlet/User dari data Google Sheets.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Tampilkan apa yang akan dilakukan tanpa benar-benar mengubah database.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        if dry_run:
            self.stdout.write(self.style.WARNING('=== MODE DRY-RUN: tidak ada perubahan disimpan ==='))

        with transaction.atomic():
            self._delete_users_except_adminpusat(dry_run)
            cities = self._ensure_cities(dry_run)
            branches = self._ensure_branches(cities, dry_run)
            self._create_leader_outlet_users(branches, dry_run)
            self._create_qc_trainer_users(cities, dry_run)
            self._create_manager_area_users(cities, dry_run)

            if dry_run:
                # Batalkan semua perubahan di atas karena ini cuma simulasi.
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS('Selesai.' if not dry_run else 'Dry-run selesai (tidak ada yang disimpan).'))

    # -------------------------------------------------------------------
    def _delete_users_except_adminpusat(self, dry_run):
        qs = User.objects.exclude(username='adminpusat')
        count = qs.count()
        self.stdout.write(f'Menghapus {count} user (semua kecuali "adminpusat")...')
        if not dry_run:
            qs.delete()

    # -------------------------------------------------------------------
    def _ensure_cities(self, dry_run):
        cities = {}
        all_city_names = set(CITY_CODE_PREFIX.keys())
        for name in sorted(all_city_names):
            city, created = City.objects.get_or_create(name=name)
            cities[name] = city
            if created:
                self.stdout.write(f'  + Kota baru: {name}')
        return cities

    # -------------------------------------------------------------------
    def _ensure_branches(self, cities, dry_run):
        branches = {}  # key: (outlet_name.lower(), kota) -> Branch

        # Hitung nomor urut kode outlet berikutnya per kota, berdasarkan
        # kode yang SUDAH ADA di database (supaya tidak bentrok).
        next_number = {}
        for prefix in CITY_CODE_PREFIX.values():
            existing_codes = Branch.objects.filter(code__startswith=f'{prefix}-').values_list('code', flat=True)
            max_n = 0
            for code in existing_codes:
                try:
                    n = int(code.split('-')[-1])
                    max_n = max(max_n, n)
                except (ValueError, IndexError):
                    continue
            next_number[prefix] = max_n + 1

        for _id, outlet_name, kota, _user, _pwd in LEADER_OUTLET_DATA:
            city = cities[kota]
            existing = Branch.objects.filter(name__iexact=outlet_name, city=city).first()
            if existing:
                branches[(outlet_name.lower(), kota)] = existing
                continue

            prefix = CITY_CODE_PREFIX[kota]
            code = f'{prefix}-{next_number[prefix]:02d}'
            next_number[prefix] += 1

            self.stdout.write(f'  + Outlet baru: {outlet_name} ({kota}) -> kode {code}')
            if not dry_run:
                branch = Branch.objects.create(name=outlet_name, code=code, city=city, is_active=True)
            else:
                branch = Branch(name=outlet_name, code=code, city=city)
            branches[(outlet_name.lower(), kota)] = branch

        return branches

    # -------------------------------------------------------------------
    def _create_leader_outlet_users(self, branches, dry_run):
        self.stdout.write('Membuat akun Leader Outlet...')
        for _id, outlet_name, kota, username, password in LEADER_OUTLET_DATA:
            branch = branches[(outlet_name.lower(), kota)]
            self._create_user(
                username=username, password=password, role=StaffProfile.Role.STAFF,
                branch=branch, dry_run=dry_run,
            )

    # -------------------------------------------------------------------
    def _create_qc_trainer_users(self, cities, dry_run):
        self.stdout.write('Membuat akun QC/Trainer...')
        for kota, username, password, phone in QC_TRAINER_DATA:
            kota_normalized = 'SAMARINDA' if kota == 'SAMAIRNDA' else kota
            city = cities[kota_normalized]
            self._create_user(
                username=username, password=password, role=StaffProfile.Role.QC_TRAINER,
                city=city, phone=phone, dry_run=dry_run,
            )

    # -------------------------------------------------------------------
    def _create_manager_area_users(self, cities, dry_run):
        self.stdout.write('Membuat akun Manager Area...')
        for kota, username, password in MANAGER_AREA_DATA:
            city = cities[kota]
            self._create_user(
                username=username, password=password, role=StaffProfile.Role.MANAGER,
                city=city, dry_run=dry_run,
            )

    # -------------------------------------------------------------------
    def _create_user(self, username, password, role, branch=None, city=None, phone='', dry_run=False):
        self.stdout.write(f'  + User: {username} ({role})')
        if dry_run:
            return
        user, created = User.objects.get_or_create(
            username=username,
            defaults={'is_staff': True},
        )
        user.set_password(password)
        user.is_staff = True
        user.save()
        StaffProfile.objects.update_or_create(
            user=user,
            defaults={
                'role': role,
                'branch': branch,
                'city': city,
                'phone': phone,
            },
        )
