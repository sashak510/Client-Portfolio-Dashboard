"""Serializers for the audit log API."""

from rest_framework import serializers

from apps.audit.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    """Read-only serializer for audit log entries."""

    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = AuditLog
        fields = (
            "id",
            "user",
            "username",
            "action",
            "model_name",
            "object_id",
            "object_repr",
            "changes",
            "ip_address",
            "timestamp",
        )
        read_only_fields = fields
