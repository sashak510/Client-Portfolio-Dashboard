"""Admin configuration for audit logs."""

from django.contrib import admin

from apps.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Read-only admin view for audit log entries."""

    list_display = ("timestamp", "user", "action", "model_name", "object_id", "object_repr")
    list_filter = ("action", "model_name", "user")
    search_fields = ("object_repr", "model_name")
    readonly_fields = [f.name for f in AuditLog._meta.get_fields() if hasattr(f, "name")]
    date_hierarchy = "timestamp"

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False
