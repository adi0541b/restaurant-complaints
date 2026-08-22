from django.conf import settings

from .models import SiteSettings


def branding(request):
    site = SiteSettings.load()
    return {
        'BRAND_NAME': site.company_name or getattr(settings, 'RESTAURANT_BRAND_NAME', 'Restoran'),
        'BRAND_LOGO_URL': site.logo.url if site.logo else None,
        'BRAND_COLOR_PRIMARY': getattr(settings, 'BRAND_COLOR_PRIMARY', '#7A1F1F'),
        'BRAND_COLOR_ACCENT': getattr(settings, 'BRAND_COLOR_ACCENT', '#C9A227'),
    }
