"""Django-filter filtersets for portfolio models."""

import django_filters

from apps.portfolio.models import Asset, Holding, Transaction


class TransactionFilter(django_filters.FilterSet):
    """Filter transactions by client, asset, type, and date range."""

    executed_at_after = django_filters.DateTimeFilter(
        field_name="executed_at", lookup_expr="gte"
    )
    executed_at_before = django_filters.DateTimeFilter(
        field_name="executed_at", lookup_expr="lte"
    )

    class Meta:
        model = Transaction
        fields = ("client", "asset", "transaction_type")


class HoldingFilter(django_filters.FilterSet):
    """Filter holdings by client and asset type."""

    asset_type = django_filters.CharFilter(field_name="asset__asset_type")

    class Meta:
        model = Holding
        fields = ("client",)


class AssetFilter(django_filters.FilterSet):
    """Filter assets by type."""

    class Meta:
        model = Asset
        fields = ("asset_type",)
