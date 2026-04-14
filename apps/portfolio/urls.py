"""URL routing for portfolio API."""

from rest_framework.routers import DefaultRouter

from apps.portfolio.views import AssetViewSet, ClientViewSet, HoldingViewSet, TransactionViewSet

router = DefaultRouter()
router.register(r"clients", ClientViewSet, basename="client")
router.register(r"assets", AssetViewSet, basename="asset")
router.register(r"holdings", HoldingViewSet, basename="holding")
router.register(r"transactions", TransactionViewSet, basename="transaction")

urlpatterns = router.urls
