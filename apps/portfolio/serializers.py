"""Serialisers for portfolio models."""

import datetime
from decimal import Decimal
from typing import Any

from rest_framework import serializers

from apps.portfolio.models import (
    Account,
    Asset,
    Dividend,
    ExchangeRate,
    Goal,
    Holding,
    Liability,
    NonInvestmentAccount,
    PortfolioSnapshot,
    RecurringContribution,
    TargetAllocation,
    Transaction,
    WatchlistItem,
)


class AssetSerializer(serializers.ModelSerializer):
    """Serialiser for the Asset model."""

    class Meta:
        model = Asset
        fields = "__all__"
        read_only_fields = ("last_price", "price_updated_at")


class AssetNestedSerializer(serializers.ModelSerializer):
    """Minimal asset representation for nested reads."""

    class Meta:
        model = Asset
        fields = ("id", "symbol", "name", "asset_type", "currency")


class HoldingSerializer(serializers.ModelSerializer):
    """Serialiser for the Holding model with computed value fields."""

    asset_detail = AssetNestedSerializer(source="asset", read_only=True)
    current_value = serializers.SerializerMethodField()
    gain_loss = serializers.SerializerMethodField()

    class Meta:
        model = Holding
        fields = (
            "id",
            "account",
            "asset",
            "asset_detail",
            "quantity",
            "average_cost",
            "current_value",
            "gain_loss",
            "notes",
        )

    def get_current_value(self, obj: Holding) -> Decimal:
        price = obj.asset.last_price if obj.asset.last_price else Decimal("0")
        if obj.asset.asset_type == Asset.AssetType.CASH:
            price = Decimal("1.0")
        elif obj.asset.asset_type == Asset.AssetType.BOND:
            price = obj.asset.face_value if obj.asset.face_value else Decimal("0")
        return obj.quantity * price

    def get_gain_loss(self, obj: Holding) -> Decimal:
        current_value = self.get_current_value(obj)
        cost_basis = obj.quantity * obj.average_cost
        return current_value - cost_basis


class TransactionSerializer(serializers.ModelSerializer):
    """Serialiser for the Transaction model."""

    asset_detail = AssetNestedSerializer(source="asset", read_only=True)

    class Meta:
        model = Transaction
        fields = (
            "id",
            "account",
            "asset",
            "asset_detail",
            "transaction_type",
            "quantity",
            "price",
            "total_value",
            "note",
            "executed_at",
            "created_at",
        )
        read_only_fields = ("total_value", "created_at")

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Auto-compute total_value and validate sell quantity."""
        attrs["total_value"] = attrs["quantity"] * attrs["price"]

        if attrs.get("transaction_type") == Transaction.TransactionType.SELL:
            account = attrs["account"]
            asset = attrs["asset"]
            try:
                holding = Holding.objects.get(account=account, asset=asset)
            except Holding.DoesNotExist:
                raise serializers.ValidationError(
                    {"detail": "No holding exists for this asset."}
                )
            if attrs["quantity"] > holding.quantity:
                raise serializers.ValidationError(
                    {"detail": "Sell quantity exceeds current holding."}
                )
        return attrs


class AccountSerializer(serializers.ModelSerializer):
    """Serialiser for the Account model."""

    total_portfolio_value = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = (
            "id",
            "account_name",
            "account_type",
            "provider",
            "total_portfolio_value",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")

    def get_total_portfolio_value(self, obj: Account) -> Decimal:
        total = Decimal("0")
        for holding in obj.holdings.select_related("asset").all():
            price = holding.asset.last_price if holding.asset.last_price else Decimal("0")
            if holding.asset.asset_type == Asset.AssetType.CASH:
                price = Decimal("1.0")
            elif holding.asset.asset_type == Asset.AssetType.BOND:
                price = holding.asset.face_value if holding.asset.face_value else Decimal("0")
            value = holding.quantity * price
            currency = getattr(holding.asset, "currency", "GBP") or "GBP"
            fx_rate = ExchangeRate.get_rate(currency, "GBP")
            total += value * fx_rate
        return total


class AccountDetailSerializer(AccountSerializer):
    """Extended account serialiser with nested holdings and recent transactions."""

    holdings = HoldingSerializer(many=True, read_only=True)
    recent_transactions = serializers.SerializerMethodField()

    class Meta(AccountSerializer.Meta):
        fields = AccountSerializer.Meta.fields + ("holdings", "recent_transactions")

    def get_recent_transactions(self, obj: Account) -> list[dict]:
        txns = obj.transactions.select_related("asset").order_by("-executed_at")[:10]
        return TransactionSerializer(txns, many=True).data


class PortfolioSummarySerializer(serializers.Serializer):
    """Read-only serialiser for portfolio summary analytics."""

    total_value = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_gain_loss = serializers.DecimalField(max_digits=14, decimal_places=2)
    equity_allocation_pct = serializers.DecimalField(max_digits=5, decimal_places=2)
    bond_allocation_pct = serializers.DecimalField(max_digits=5, decimal_places=2)
    cash_allocation_pct = serializers.DecimalField(max_digits=5, decimal_places=2)
    top_holdings = serializers.ListField()
    total_dividends = serializers.DecimalField(max_digits=14, decimal_places=2)


class HoldingPerformanceSerializer(serializers.Serializer):
    """Per-holding breakdown within a performance response."""

    symbol = serializers.CharField()
    name = serializers.CharField()
    asset_type = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=14, decimal_places=4)
    cost_basis = serializers.DecimalField(max_digits=14, decimal_places=2)
    current_value = serializers.DecimalField(max_digits=14, decimal_places=2)
    gain_loss = serializers.DecimalField(max_digits=14, decimal_places=2)
    return_pct = serializers.DecimalField(max_digits=8, decimal_places=2)


class PerformanceSerializer(serializers.Serializer):
    """Read-only serialiser for portfolio performance analytics."""

    account_id = serializers.IntegerField()
    account_name = serializers.CharField()
    period_days = serializers.IntegerField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    current_value = serializers.DecimalField(max_digits=14, decimal_places=2)
    cost_basis = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_gain_loss = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_return_pct = serializers.DecimalField(max_digits=8, decimal_places=2)
    transactions_in_period = serializers.IntegerField()
    net_invested_in_period = serializers.DecimalField(max_digits=14, decimal_places=2)
    holdings_breakdown = HoldingPerformanceSerializer(many=True)


class TargetAllocationSerializer(serializers.ModelSerializer):
    """Serialiser for the TargetAllocation model."""

    class Meta:
        model = TargetAllocation
        fields = ("id", "account", "asset_type", "target_percentage")


class DividendSerializer(serializers.ModelSerializer):
    """Serialiser for the Dividend model."""

    holding_detail = serializers.SerializerMethodField()

    class Meta:
        model = Dividend
        fields = (
            "id",
            "holding",
            "holding_detail",
            "amount",
            "per_share_amount",
            "ex_date",
            "payment_date",
            "created_at",
        )
        read_only_fields = ("created_at",)

    def get_holding_detail(self, obj: Dividend) -> dict:
        return {
            "id": obj.holding.id,
            "account_id": obj.holding.account_id,
            "symbol": obj.holding.asset.symbol,
            "name": obj.holding.asset.name,
        }


class WatchlistAssetSerializer(serializers.ModelSerializer):
    """Read-only asset detail for watchlist items."""

    class Meta:
        model = Asset
        fields = ("id", "symbol", "name", "asset_type", "last_price")


class WatchlistItemSerializer(serializers.ModelSerializer):
    """Serialiser for the WatchlistItem model."""

    asset_detail = WatchlistAssetSerializer(source="asset", read_only=True)

    class Meta:
        model = WatchlistItem
        fields = (
            "id",
            "asset",
            "asset_detail",
            "target_price",
            "notes",
            "created_at",
        )
        read_only_fields = ("created_at",)


class NonInvestmentAccountSerializer(serializers.ModelSerializer):
    """Serialiser for the NonInvestmentAccount model."""

    class Meta:
        model = NonInvestmentAccount
        fields = (
            "id",
            "name",
            "account_type",
            "balance",
            "currency",
            "notes",
            "updated_at",
        )
        read_only_fields = ("updated_at",)


class LiabilitySerializer(serializers.ModelSerializer):
    """Serialiser for the Liability model."""

    class Meta:
        model = Liability
        fields = ("id", "name", "liability_type", "balance", "notes", "updated_at")
        read_only_fields = ("updated_at",)


class RecurringContributionSerializer(serializers.ModelSerializer):
    """Serialiser for the RecurringContribution model."""

    account_name = serializers.CharField(source="account.account_name", read_only=True)

    class Meta:
        model = RecurringContribution
        fields = (
            "id",
            "account",
            "account_name",
            "amount",
            "frequency",
            "start_date",
            "next_due_date",
            "notes",
            "is_active",
        )


class GoalSerializer(serializers.ModelSerializer):
    """Serialiser for the Goal model with computed progress fields."""

    current_value = serializers.SerializerMethodField()
    progress_pct = serializers.SerializerMethodField()
    days_remaining = serializers.SerializerMethodField()
    on_track = serializers.SerializerMethodField()
    account_name = serializers.CharField(source="account.account_name", read_only=True, default=None)

    class Meta:
        model = Goal
        fields = (
            "id",
            "name",
            "account",
            "account_name",
            "target_amount",
            "target_date",
            "notes",
            "created_at",
            "current_value",
            "progress_pct",
            "days_remaining",
            "on_track",
        )
        read_only_fields = ("created_at",)

    def _get_current_value(self, obj: "Goal") -> Decimal:
        """Return current portfolio value for the linked account (or all accounts)."""
        if obj.account:
            accounts = [obj.account]
        else:
            accounts = list(obj.user.accounts.all())

        total = Decimal("0")
        for account in accounts:
            for holding in account.holdings.select_related("asset").all():
                price = holding.asset.last_price if holding.asset.last_price else Decimal("0")
                if holding.asset.asset_type == Asset.AssetType.CASH:
                    price = Decimal("1.0")
                elif holding.asset.asset_type == Asset.AssetType.BOND:
                    price = holding.asset.face_value if holding.asset.face_value else Decimal("0")
                value = holding.quantity * price
                fx_rate = ExchangeRate.get_rate(getattr(holding.asset, "currency", "GBP") or "GBP")
                total += value * fx_rate
        return total

    def get_current_value(self, obj: "Goal") -> Decimal:
        return self._get_current_value(obj)

    def get_progress_pct(self, obj: "Goal") -> Decimal:
        target = obj.target_amount
        if not target or target <= 0:
            return Decimal("0")
        current = self._get_current_value(obj)
        pct = (current / target) * Decimal("100")
        return min(pct, Decimal("100"))

    def get_days_remaining(self, obj: "Goal") -> int:
        delta = obj.target_date - datetime.date.today()
        return max(delta.days, 0)

    def get_on_track(self, obj: "Goal") -> bool:
        """Linear projection: if current growth rate is maintained, will the target be hit?"""
        current = self._get_current_value(obj)
        target = obj.target_amount
        if not target or target <= 0:
            return True
        if current >= target:
            return True

        days_remaining = self.get_days_remaining(obj)
        if days_remaining <= 0:
            return current >= target

        # Days elapsed since goal creation
        days_elapsed = (datetime.date.today() - obj.created_at.date()).days
        if days_elapsed <= 0:
            # No history yet — assume on track if we have some progress
            return current > Decimal("0")

        # Linear projection: grow current at the same daily rate
        growth_per_day = current / Decimal(str(days_elapsed))
        projected = current + growth_per_day * Decimal(str(days_remaining))
        return projected >= target


class PortfolioSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = PortfolioSnapshot
        fields = ("id", "date", "total_value", "account_snapshots", "created_at", "updated_at")
        read_only_fields = fields

