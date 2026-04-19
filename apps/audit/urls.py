"""URL routing for audit log API."""

from rest_framework.routers import DefaultRouter

from apps.audit.views import AuditLogViewSet

router = DefaultRouter()
router.register(r"", AuditLogViewSet, basename="auditlog")

urlpatterns = router.urls
