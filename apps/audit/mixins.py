"""DRF ViewSet mixin for automatic audit logging."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from rest_framework.response import Response

from apps.audit.models import AuditLog

SKIP_FIELDS = {"id", "pk", "created_at", "updated_at"}


class AuditLogMixin:
    """Mixin for ModelViewSet that logs create, update, and delete operations.

    Overrides the action methods (create, update, destroy) rather than
    perform_* so that audit logging works even when a ViewSet provides
    its own perform_create / perform_update.
    """

    def _get_client_ip(self, request) -> str | None:
        """Extract client IP from the request, checking X-Forwarded-For first."""
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

    def _serialize_value(self, value: Any) -> Any:
        """Convert non-JSON-serializable types to strings."""
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        return value

    def _get_field_values(self, instance) -> dict[str, Any]:
        """Snapshot all concrete field values from a model instance."""
        values = {}
        for field in instance._meta.concrete_fields:
            if field.name in SKIP_FIELDS:
                continue
            value = getattr(instance, field.attname)
            values[field.name] = self._serialize_value(value)
        return values

    def _get_model_class(self):
        """Return the model class for the current viewset."""
        return self.get_queryset().model

    def create(self, request, *args, **kwargs) -> Response:
        """Wrap create to log an audit entry after successful creation."""
        response = super().create(request, *args, **kwargs)
        if response.status_code == 201:
            model = self._get_model_class()
            instance = model.objects.get(pk=response.data["id"])
            field_values = self._get_field_values(instance)
            changes = {k: {"old": None, "new": v} for k, v in field_values.items()}
            AuditLog.objects.create(
                user=request.user,
                action=AuditLog.Action.CREATE,
                model_name=model.__name__,
                object_id=instance.pk,
                object_repr=str(instance)[:200],
                changes=changes,
                ip_address=self._get_client_ip(request),
            )
        return response

    def update(self, request, *args, **kwargs) -> Response:
        """Wrap update to log only the fields that actually changed."""
        instance = self.get_object()
        old_values = self._get_field_values(instance)
        response = super().update(request, *args, **kwargs)
        if response.status_code == 200:
            instance.refresh_from_db()
            new_values = self._get_field_values(instance)
            changes = {}
            for field_name, new_val in new_values.items():
                old_val = old_values.get(field_name)
                if old_val != new_val:
                    changes[field_name] = {"old": old_val, "new": new_val}
            if changes:
                AuditLog.objects.create(
                    user=request.user,
                    action=AuditLog.Action.UPDATE,
                    model_name=instance.__class__.__name__,
                    object_id=instance.pk,
                    object_repr=str(instance)[:200],
                    changes=changes,
                    ip_address=self._get_client_ip(request),
                )
        return response

    def destroy(self, request, *args, **kwargs) -> Response:
        """Capture field values before deletion then log a DELETE audit entry."""
        instance = self.get_object()
        field_values = self._get_field_values(instance)
        changes = {k: {"old": v, "new": None} for k, v in field_values.items()}
        object_id = instance.pk
        object_repr = str(instance)[:200]
        model_name = instance.__class__.__name__
        ip_address = self._get_client_ip(request)
        response = super().destroy(request, *args, **kwargs)
        if response.status_code == 204:
            AuditLog.objects.create(
                user=request.user,
                action=AuditLog.Action.DELETE,
                model_name=model_name,
                object_id=object_id,
                object_repr=object_repr,
                changes=changes,
                ip_address=ip_address,
            )
        return response
