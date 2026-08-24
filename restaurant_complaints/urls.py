from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve as static_serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('complaints.urls')),
]

# File media (logo perusahaan, foto bukti komplain) SELALU disajikan lewat Django,
# baik saat DEBUG=True maupun DEBUG=False. Ini karena hosting ini tidak memiliki
# konfigurasi web server terpisah (Nginx/Apache) yang menangani folder /media/ secara
# langsung -- semua request diteruskan ke aplikasi Django lewat reverse proxy panel.
# Untuk aplikasi dengan trafik sangat tinggi, sebaiknya media disajikan lewat
# Nginx/Apache langsung atau storage eksternal (S3, dll), tapi untuk skala aplikasi
# ini, menyajikannya lewat Django sudah cukup memadai.
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', static_serve, {'document_root': settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / 'complaints' / 'static')
