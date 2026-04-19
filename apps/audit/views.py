"""Read-only API for audit logs (admin only)."""

from rest_framework.permissions import IsAdminUser
from rest_framework.viewsets import ReadOnlyModelViewSet

from apps.audit.filters import AuditLogFilter
from apps.audit.models import AuditLog
from apps.audit.serializers import AuditLogSerializer


class AuditLogViewSet(ReadOnlyModelViewSet):
    """List and retrieve audit log entries. Admin-only access."""

    queryset = AuditLog.objects.select_related("user").all()
    serializer_class = AuditLogSerializer
    filterset_class = AuditLogFilter
    permission_classes = [IsAdminUser]
