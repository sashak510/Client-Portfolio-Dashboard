"""Serialisers for portfolio models."""

from decimal import Decimal
from typing import Any

from rest_framework import serializers

from apps.portfolio.models import Asset, Client, Holding, Transaction


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
        fields = ("id", "symbol", "name", "asset_type")


class HoldingSerializer(serializers.ModelSerializer):
    """Serialiser for the Holding model with computed value fields."""

    asset_detail = AssetNestedSerializer(source="asset", read_only=True)
    current_value = serializers.SerializerMethodField()
    gain_loss = serializers.SerializerMethodField()

    class Meta:
        model = Holding
        fields = (
            "id",
            "client",
            "asset",
            "asset_detail",
            "quantity",
            "average_cost",
            "current_value",
            "gain_loss",
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
            "client",
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
            client = attrs["client"]
            asset = attrs["asset"]
            try:
                holding = Holding.objects.get(client=client, asset=asset)
            except Holding.DoesNotExist:
                raise serializers.ValidationError(
                    {"detail": "No holding exists for this asset."}
                )
            if attrs["quantity"] > holding.quantity:
                raise serializers.ValidationError(
                    {"detail": "Sell quantity exceeds current holding."}
                )
        return attrs


class ClientSerializer(serializers.ModelSerializer):
    """Serialiser for the Client model."""

    total_portfolio_value = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "phone",
            "total_portfolio_value",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")

    def get_total_portfolio_value(self, obj: Client) -> Decimal:
        total = Decimal("0")
        for holding in obj.holdings.select_related("asset").all():
            price = holding.asset.last_price if holding.asset.last_price else Decimal("0")
            if holding.asset.asset_type == Asset.AssetType.CASH:
                price = Decimal("1.0")
            elif holding.asset.asset_type == Asset.AssetType.BOND:
                price = holding.asset.face_value if holding.asset.face_value else Decimal("0")
            total += holding.quantity * price
        return total


class ClientDetailSerializer(ClientSerializer):
    """Extended client serialiser with nested holdings and recent transactions."""

    holdings = HoldingSerializer(many=True, read_only=True)
    recent_transactions = serializers.SerializerMethodField()

    class Meta(ClientSerializer.Meta):
        fields = ClientSerializer.Meta.fields + ("holdings", "recent_transactions")

    def get_recent_transactions(self, obj: Client) -> list[dict]:
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
