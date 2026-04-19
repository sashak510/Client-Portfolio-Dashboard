"""Django-filter filtersets for portfolio models."""

import django_filters

from apps.portfolio.models import Asset, Holding, Transaction


class TransactionFilter(django_filters.FilterSet):
    """Filter transactions by account, asset, type, and date range."""

    executed_at_after = django_filters.DateTimeFilter(
        field_name="executed_at", lookup_expr="gte"
    )
    executed_at_before = django_filters.DateTimeFilter(
        field_name="executed_at", lookup_expr="lte"
    )

    class Meta:
        model = Transaction
        fields = ("account", "asset", "transaction_type")


class HoldingFilter(django_filters.FilterSet):
    """Filter holdings by account and asset type."""

    asset_type = django_filters.CharFilter(field_name="asset__asset_type")

    class Meta:
        model = Holding
        fields = ("account",)


class AssetFilter(django_filters.FilterSet):
    """Filter assets by type."""

    class Meta:
        model = Asset
        fields = ("asset_type",)
