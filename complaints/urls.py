from django.urls import path

from . import views

app_name = 'complaints'

urlpatterns = [
    # Publik - Pelanggan
    path('', views.home_submission, name='home'),
    path('sukses/<str:code>/', views.submission_success, name='submission_success'),
    path('cek-status/', views.status_check, name='status_check'),
    path('rating/<str:code>/', views.satisfaction_rating, name='satisfaction_rating'),

    # Auth
    path('login/', views.StaffLoginView.as_view(), name='login'),
    path('logout/', views.StaffLogoutView.as_view(), name='logout'),
    path('ganti-password/', views.StaffPasswordChangeView.as_view(), name='password_change'),
    path('ganti-password/selesai/', views.StaffPasswordChangeDoneView.as_view(), name='password_change_done'),

    # Internal - Staff / Manager / Admin Pusat
    path('dashboard/', views.dashboard, name='dashboard'),
    path('komplain/', views.complaint_list, name='complaint_list'),
    path('komplain/export/', views.export_complaints_excel, name='export_excel'),
    path('komplain/<int:pk>/', views.complaint_detail, name='complaint_detail'),

    # Panel Admin Pusat
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('admin-panel/users/', views.user_list, name='user_list'),
    path('admin-panel/users/baru/', views.user_create, name='user_create'),
    path('admin-panel/users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('admin-panel/users/<int:pk>/reset-password/', views.user_reset_password, name='user_reset_password'),
    path('admin-panel/cabang/', views.branch_list, name='branch_list'),
    path('admin-panel/cabang/baru/', views.branch_create, name='branch_create'),
    path('admin-panel/cabang/<int:pk>/edit/', views.branch_edit, name='branch_edit'),
    path('admin-panel/kota/', views.city_list, name='city_list'),
    path('admin-panel/kota/baru/', views.city_create, name='city_create'),
    path('admin-panel/kota/<int:pk>/edit/', views.city_edit, name='city_edit'),
    path('admin-panel/sumber-komplain/', views.source_list, name='source_list'),
    path('admin-panel/sumber-komplain/baru/', views.source_create, name='source_create'),
    path('admin-panel/sumber-komplain/<int:pk>/edit/', views.source_edit, name='source_edit'),
    path('admin-panel/rincian-komplain/', views.detail_item_list, name='detail_item_list'),
    path('admin-panel/rincian-komplain/baru/', views.detail_item_create, name='detail_item_create'),
    path('admin-panel/rincian-komplain/<int:pk>/edit/', views.detail_item_edit, name='detail_item_edit'),
    path('admin-panel/pengaturan/', views.site_settings_edit, name='site_settings_edit'),
]
