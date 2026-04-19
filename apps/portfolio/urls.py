"""URL routing for portfolio API."""

# fmt: off
# ruff: noqa
from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.portfolio.views import (
    AccountViewSet,
    AssetViewSet,
    ContributionHistoryView,
    CSVImportView,
    CSVSampleView,
    DividendViewSet,
    ExportDataView,
    GoalViewSet,
    HoldingViewSet,
    LiabilityViewSet,
    NetWorthSummaryView,
    NonInvestmentAccountViewSet,
    RecurringContributionViewSet,
    SnapshotViewSet,
    TakeSnapshotView,
    TargetAllocationViewSet,
    TransactionViewSet,
    WatchlistItemViewSet,
)

router = DefaultRouter()
router.register(r"accounts", AccountViewSet, basename="account")
router.register(r"assets", AssetViewSet, basename="asset")
router.register(r"holdings", HoldingViewSet, basename="holding")
router.register(r"transactions", TransactionViewSet, basename="transaction")
router.register(r"target-allocations", TargetAllocationViewSet, basename="targetallocation")
router.register(r"dividends", DividendViewSet, basename="dividend")
router.register(r"watchlist", WatchlistItemViewSet, basename="watchlistitem")
router.register(r"net-worth-accounts", NonInvestmentAccountViewSet, basename="networthaccount")
router.register(r"recurring-contributions", RecurringContributionViewSet, basename="recurringcontribution")
router.register(r"goals", GoalViewSet, basename="goal")
router.register(r"snapshots", SnapshotViewSet, basename="snapshot")
router.register(r"liabilities", LiabilityViewSet, basename="liability")

urlpatterns = [
    path("import/", CSVImportView.as_view(), name="csv-import"),
    path("import/sample/<str:broker>/", CSVSampleView.as_view(), name="csv-sample"),
    path("export/", ExportDataView.as_view(), name="export-data"),
    path("net-worth/", NetWorthSummaryView.as_view(), name="net-worth-summary"),
    path("contribution-history/", ContributionHistoryView.as_view(), name="contribution-history"),
    path("snapshots/take/", TakeSnapshotView.as_view(), name="snapshot-take"),
] + router.urls
