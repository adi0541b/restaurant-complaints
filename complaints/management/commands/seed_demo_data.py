import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from complaints.models import Branch, Complaint, StaffProfile

User = get_user_model()

BRANCHES = [
    {'name': 'Rasa Nusantara - Kemang', 'code': 'JKT-01', 'city': 'Jakarta'},
    {'name': 'Rasa Nusantara - Dago', 'code': 'BDG-01', 'city': 'Bandung'},
    {'name': 'Rasa Nusantara - Simpang Lima', 'code': 'SMG-01', 'city': 'Semarang'},
]

CUSTOMER_NAMES = [
    'Budi Santoso', 'Siti Aminah', 'Andi Wijaya', 'Rina Kartika', 'Dedi Kurniawan',
    'Maya Sari', 'Agus Setiawan', 'Lina Marlina', 'Hendra Gunawan', 'Putri Wulandari',
]

SAMPLE_DESCRIPTIONS = {
    'makanan': 'Nasi goreng yang saya pesan rasanya terlalu asin dan porsinya tidak sesuai menu.',
    'pelayanan': 'Pelayan kurang responsif, sudah menunggu 20 menit belum juga dicatat pesanannya.',
    'kebersihan': 'Meja dan kursi terasa masih kotor saat kami datang, ada sisa makanan pengunjung sebelumnya.',
    'kecepatan': 'Pesanan baru datang setelah 45 menit padahal restoran sedang sepi.',
    'fasilitas': 'AC di area smoking room tidak berfungsi, ruangan sangat panas dan pengap.',
    'pembayaran': 'Struk pembayaran tidak sesuai dengan pesanan, ada item yang double charge.',
    'lainnya': 'Ingin memberi masukan terkait tata letak parkir yang kurang jelas.',
}


class Command(BaseCommand):
    help = 'Mengisi data demo: cabang, staff, dan contoh komplain.'

    def add_arguments(self, parser):
        parser.add_argument('--complaints', type=int, default=25,
                             help='Jumlah contoh komplain yang dibuat (default: 25)')

    def handle(self, *args, **options):
        self.stdout.write('Membuat data demo...')

        # --- Admin Pusat ---
        admin_user, created = User.objects.get_or_create(
            username='adminpusat',
            defaults={'first_name': 'Admin', 'last_name': 'Pusat', 'email': 'admin@restoran.example.com',
                      'is_staff': True, 'is_superuser': True},
        )
        if created:
            admin_user.set_password('admin12345')
            admin_user.save()
        StaffProfile.objects.get_or_create(
            user=admin_user, defaults={'role': StaffProfile.Role.ADMIN, 'phone': '081200000001'},
        )

        # --- Cabang + Manager + Staff ---
        branches = []
        for i, b in enumerate(BRANCHES, start=1):
            branch, _ = Branch.objects.get_or_create(
                code=b['code'],
                defaults={'name': b['name'], 'city': b['city'], 'address': f"Jl. Contoh No. {i}, {b['city']}"},
            )
            branches.append(branch)

            manager_username = f'manager{i}'
            manager_user, created = User.objects.get_or_create(
                username=manager_username,
                defaults={'first_name': 'Manager', 'last_name': b['city'],
                          'email': f'{manager_username}@restoran.example.com', 'is_staff': True},
            )
            if created:
                manager_user.set_password('manager12345')
                manager_user.save()
            StaffProfile.objects.get_or_create(
                user=manager_user,
                defaults={'role': StaffProfile.Role.MANAGER, 'branch': branch, 'phone': f'08130000000{i}'},
            )
            branch.manager = manager_user
            branch.save(update_fields=['manager'])

            staff_username = f'staff{i}'
            staff_user, created = User.objects.get_or_create(
                username=staff_username,
                defaults={'first_name': 'Staff', 'last_name': b['city'],
                          'email': f'{staff_username}@restoran.example.com', 'is_staff': True},
            )
            if created:
                staff_user.set_password('staff12345')
                staff_user.save()
            StaffProfile.objects.get_or_create(
                user=staff_user,
                defaults={'role': StaffProfile.Role.STAFF, 'branch': branch, 'phone': f'08140000000{i}'},
            )

        # --- Contoh komplain ---
        n = options['complaints']
        categories = list(Complaint.Category.values)
        severities = list(Complaint.Severity.values)
        statuses = list(Complaint.Status.values)

        created_count = 0
        for i in range(n):
            branch = random.choice(branches)
            category = random.choice(categories)
            severity = random.choice(severities)
            status = random.choices(
                statuses, weights=[0.2, 0.15, 0.2, 0.35, 0.1]
            )[0]
            days_ago = random.randint(0, 20)

            complaint = Complaint.objects.create(
                customer_name=random.choice(CUSTOMER_NAMES),
                customer_phone=f'0812{random.randint(10000000, 99999999)}',
                customer_email='' if random.random() < 0.4 else 'pelanggan@contoh.com',
                branch=branch,
                table_number=str(random.randint(1, 30)),
                category=category,
                severity=severity,
                description=SAMPLE_DESCRIPTIONS.get(category, 'Komplain pelanggan.'),
                status=status,
            )
            # Geser waktu dibuat agar variatif (beberapa lampau, untuk demo overdue)
            created_at = timezone.now() - timedelta(days=days_ago, hours=random.randint(0, 23))
            Complaint.objects.filter(pk=complaint.pk).update(created_at=created_at)
            complaint.refresh_from_db()
            complaint.sla_deadline = complaint.calculate_sla_deadline()
            if status == Complaint.Status.SELESAI:
                complaint.resolved_at = created_at + timedelta(hours=random.randint(1, 48))
                if random.random() < 0.7:
                    complaint.satisfaction_rating = random.randint(3, 5)
                    complaint.rated_at = complaint.resolved_at + timedelta(hours=2)
            complaint.save()
            created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Selesai. {len(branches)} cabang, {len(branches) * 2 + 1} akun staff, '
            f'{created_count} contoh komplain dibuat.'
        ))
        self.stdout.write('Login admin pusat: adminpusat / admin12345')
        self.stdout.write('Login manager: manager1 / manager12345 (dst. manager2, manager3)')
        self.stdout.write('Login staff: staff1 / staff12345 (dst. staff2, staff3)')
