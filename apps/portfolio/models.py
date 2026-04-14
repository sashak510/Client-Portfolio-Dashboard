"""Portfolio models: Client, Asset, Holding, Transaction."""

from django.contrib.auth.models import User
from django.db import models


class Client(models.Model):
    """An investment client managed by an adviser."""

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="clients")
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("last_name", "first_name")

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"


class Asset(models.Model):
    """A tradeable asset (equity, bond, or cash)."""

    class AssetType(models.TextChoices):
        EQUITY = "equity", "Equity"
        BOND = "bond", "Bond"
        CASH = "cash", "Cash"

    symbol = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=200)
    asset_type = models.CharField(max_length=10, choices=AssetType.choices)
    face_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    coupon_rate = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    maturity_date = models.DateField(null=True, blank=True)
    last_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    price_updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.symbol} ({self.get_asset_type_display()})"


class Holding(models.Model):
    """A client's position in a specific asset."""

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="holdings")
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="holdings")
    quantity = models.DecimalField(max_digits=14, decimal_places=4)
    average_cost = models.DecimalField(max_digits=12, decimal_places=4)

    class Meta:
        unique_together = ("client", "asset")

    def __str__(self) -> str:
        return f"{self.client} - {self.asset.symbol} x{self.quantity}"


class Transaction(models.Model):
    """A buy/sell/deposit/withdraw transaction."""

    class TransactionType(models.TextChoices):
        BUY = "buy", "Buy"
        SELL = "sell", "Sell"
        DEPOSIT = "deposit", "Deposit"
        WITHDRAW = "withdraw", "Withdraw"

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="transactions")
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="transactions")
    transaction_type = models.CharField(max_length=10, choices=TransactionType.choices)
    quantity = models.DecimalField(max_digits=14, decimal_places=4)
    price = models.DecimalField(max_digits=12, decimal_places=4)
    total_value = models.DecimalField(max_digits=14, decimal_places=2)
    note = models.TextField(blank=True)
    executed_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-executed_at",)

    def __str__(self) -> str:
        return f"{self.get_transaction_type_display()} {self.asset.symbol} for {self.client}"
