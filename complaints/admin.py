from django.contrib import admin
from django.utils.html import format_html

from .models import Branch, City, Complaint, ComplaintTimelineEntry, SiteSettings, StaffProfile


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'updated_at')

    def has_add_permission(self, request):
        # Singleton: cegah pembuatan baris kedua dari Django Admin
        return not SiteSettings.objects.exists()


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'city', 'manager', 'is_active')
    list_filter = ('is_active', 'city')
    search_fields = ('name', 'code', 'city__name')


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'branch', 'city', 'phone', 'is_active_pic')
    list_filter = ('role', 'branch', 'city', 'is_active_pic')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'phone')
    autocomplete_fields = ('user',)


class TimelineInline(admin.TabularInline):
    model = ComplaintTimelineEntry
    extra = 0
    readonly_fields = ('old_status', 'new_status', 'note', 'changed_by', 'created_at')
    can_delete = False


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = (
        'code', 'customer_name', 'branch', 'category', 'severity_badge',
        'status_badge', 'overdue_flag', 'created_at',
    )
    list_filter = ('status', 'severity', 'category', 'branch')
    search_fields = ('code', 'customer_name', 'customer_phone', 'customer_email', 'description')
    readonly_fields = ('code', 'sla_deadline', 'created_at', 'updated_at')
    inlines = [TimelineInline]
    fieldsets = (
        ('Identitas Komplain', {'fields': ('code', 'status', 'severity')}),
        ('Data Pelanggan', {
            'fields': ('customer_name', 'customer_phone', 'customer_email'),
        }),
        ('Konteks Kejadian', {
            'fields': ('branch', 'table_number', 'visit_date', 'order_number'),
        }),
        ('Isi Komplain', {
            'fields': ('category', 'description', 'photo_evidence'),
        }),
        ('Penanganan', {
            'fields': ('assigned_to', 'resolution_notes', 'internal_notes', 'solution_confirmed', 'validation_notes', 'sla_deadline', 'resolved_at'),
        }),
        ('Validasi', {
            'fields': ('validated', 'validated_by', 'validated_at'),
        }),
        ('Kepuasan Pelanggan', {
            'fields': ('satisfaction_rating', 'satisfaction_feedback', 'rated_at'),
        }),
        ('Metadata', {'fields': ('created_at', 'updated_at')}),
    )

    @admin.display(description='Tingkat')
    def severity_badge(self, obj):
        colors = {'kritis': '#B00020', 'tinggi': '#C9A227', 'sedang': '#3B6E8F', 'rendah': '#5B8C5A'}
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:10px;font-size:11px;">{}</span>',
            colors.get(obj.severity, '#888'), obj.get_severity_display(),
        )

    @admin.display(description='Status')
    def status_badge(self, obj):
        colors = {
            'baru': '#7A1F1F', 'ditinjau': '#C9A227', 'diproses': '#3B6E8F',
            'selesai': '#5B8C5A', 'ditolak': '#888888',
        }
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;border-radius:10px;font-size:11px;">{}</span>',
            colors.get(obj.status, '#888'), obj.get_status_display(),
        )

    @admin.display(description='SLA', boolean=True)
    def overdue_flag(self, obj):
        return obj.is_overdue


@admin.register(ComplaintTimelineEntry)
class ComplaintTimelineEntryAdmin(admin.ModelAdmin):
    list_display = ('complaint', 'old_status', 'new_status', 'changed_by', 'created_at')
    list_filter = ('new_status',)
