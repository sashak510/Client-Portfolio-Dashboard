"""Django-filter filtersets for audit logs."""

import django_filters

from apps.audit.models import AuditLog


class AuditLogFilter(django_filters.FilterSet):
    """Filter audit logs by model, action, user, object, and timestamp range."""

    timestamp_after = django_filters.DateTimeFilter(
        field_name="timestamp", lookup_expr="gte"
    )
    timestamp_before = django_filters.DateTimeFilter(
        field_name="timestamp", lookup_expr="lte"
    )

    class Meta:
        model = AuditLog
        fields = ("model_name", "action", "user", "object_id")
