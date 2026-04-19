"""Portfolio models: Account, Asset, Holding, Transaction."""

from django.contrib.auth.models import User
from django.db import models


class Account(models.Model):
    """A personal investment account (e.g. ISA, SIPP, GIA)."""

    class AccountType(models.TextChoices):
        ISA = "isa", "ISA"
        SIPP = "sipp", "SIPP"
        GIA = "gia", "GIA"
        BROKERAGE = "brokerage", "Brokerage"
        SAVINGS = "savings", "Savings"
        OTHER = "other", "Other"

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="accounts")
    account_name = models.CharField(max_length=200)
    account_type = models.CharField(
        max_length=20, choices=AccountType.choices, default=AccountType.OTHER
    )
    provider = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("account_name",)

    def __str__(self) -> str:
        return self.account_name


class Asset(models.Model):
    """A tradeable asset (equity, bond, or cash)."""

    class AssetType(models.TextChoices):
        EQUITY = "equity", "Equity"
        BOND = "bond", "Bond"
        CASH = "cash", "Cash"

    class Currency(models.TextChoices):
        GBP = "GBP", "GBP"
        USD = "USD", "USD"
        EUR = "EUR", "EUR"

    symbol = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=200)
    asset_type = models.CharField(max_length=10, choices=AssetType.choices)
    currency = models.CharField(max_length=3, choices=Currency.choices, default="GBP")
    face_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    coupon_rate = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    maturity_date = models.DateField(null=True, blank=True)
    last_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    price_updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.symbol} ({self.get_asset_type_display()})"


class ExchangeRate(models.Model):
    """Static exchange rates for converting foreign currencies to GBP."""

    from_currency = models.CharField(max_length=3, choices=Asset.Currency.choices)
    to_currency = models.CharField(max_length=3, choices=Asset.Currency.choices, default="GBP")
    rate = models.DecimalField(max_digits=10, decimal_places=6)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("from_currency", "to_currency")

    def __str__(self) -> str:
        return f"{self.from_currency}/{self.to_currency} = {self.rate}"

    @staticmethod
    def get_rate(from_currency: str, to_currency: str = "GBP") -> "Decimal":
        """Return the exchange rate, defaulting to 1.0 for same-currency pairs."""
        from decimal import Decimal

        if from_currency == to_currency:
            return Decimal("1")
        try:
            return ExchangeRate.objects.get(
                from_currency=from_currency, to_currency=to_currency
            ).rate
        except ExchangeRate.DoesNotExist:
            # Fallback static rates
            fallback = {
                ("USD", "GBP"): Decimal("0.79"),
                ("EUR", "GBP"): Decimal("0.86"),
            }
            return fallback.get((from_currency, to_currency), Decimal("1"))


class Holding(models.Model):
    """A position in a specific asset within an account."""

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="holdings")
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="holdings")
    quantity = models.DecimalField(max_digits=14, decimal_places=4)
    average_cost = models.DecimalField(max_digits=12, decimal_places=4)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("account", "asset")

    def __str__(self) -> str:
        return f"{self.account} - {self.asset.symbol} x{self.quantity}"


class Transaction(models.Model):
    """A buy/sell/deposit/withdraw transaction."""

    class TransactionType(models.TextChoices):
        BUY = "buy", "Buy"
        SELL = "sell", "Sell"
        DEPOSIT = "deposit", "Deposit"
        WITHDRAW = "withdraw", "Withdraw"

    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="transactions")
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
        return f"{self.get_transaction_type_display()} {self.asset.symbol} for {self.account}"


class TargetAllocation(models.Model):
    """Target allocation percentage for an asset type within an account."""

    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="target_allocations"
    )
    asset_type = models.CharField(max_length=10, choices=Asset.AssetType.choices)
    target_percentage = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        unique_together = ("account", "asset_type")

    def __str__(self) -> str:
        return f"{self.account} - {self.get_asset_type_display()} target {self.target_percentage}%"


class Dividend(models.Model):
    """A dividend payment received for a holding."""

    holding = models.ForeignKey(
        Holding, on_delete=models.CASCADE, related_name="dividends"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    per_share_amount = models.DecimalField(max_digits=12, decimal_places=4)
    ex_date = models.DateField()
    payment_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-payment_date",)

    def __str__(self) -> str:
        return f"Dividend {self.amount} for {self.holding}"


class WatchlistItem(models.Model):
    """An asset on a user's watchlist with optional target price and notes."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="watchlist_items")
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name="watchlist_items")
    target_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "asset")
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.user.username} watching {self.asset.symbol}"


class NonInvestmentAccount(models.Model):
    """A non-investment financial account (savings, property, debt, etc.)."""

    class AccountType(models.TextChoices):
        SAVINGS = "savings", "Savings"
        PROPERTY = "property", "Property"
        DEBT = "debt", "Debt"
        OTHER = "other", "Other"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="non_investment_accounts")
    name = models.CharField(max_length=200)
    account_type = models.CharField(
        max_length=20, choices=AccountType.choices, default=AccountType.OTHER
    )
    balance = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default="GBP")
    notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return f"{self.name} ({self.account_type})"


class RecurringContribution(models.Model):
    """A recurring scheduled contribution to an investment account."""

    class Frequency(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        ANNUALLY = "annually", "Annually"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="recurring_contributions")
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="recurring_contributions")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    frequency = models.CharField(max_length=20, choices=Frequency.choices, default=Frequency.MONTHLY)
    start_date = models.DateField()
    next_due_date = models.DateField()
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("next_due_date",)

    def __str__(self) -> str:
        return f"{self.get_frequency_display()} £{self.amount} → {self.account}"


class Goal(models.Model):
    """A financial goal, optionally linked to a specific account."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="goals")
    name = models.CharField(max_length=200)
    account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, related_name="goals", null=True, blank=True
    )
    target_amount = models.DecimalField(max_digits=14, decimal_places=2)
    target_date = models.DateField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("target_date",)

    def __str__(self) -> str:
        return f"{self.name} — target {self.target_amount}"


class Liability(models.Model):
    """A financial liability (mortgage, loan, credit card, etc.)."""

    class LiabilityType(models.TextChoices):
        MORTGAGE = "mortgage", "Mortgage"
        LOAN = "loan", "Loan"
        CREDIT_CARD = "credit_card", "Credit Card"
        OTHER = "other", "Other"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="liabilities")
    name = models.CharField(max_length=200)
    liability_type = models.CharField(
        max_length=20, choices=LiabilityType.choices, default=LiabilityType.OTHER
    )
    balance = models.DecimalField(max_digits=14, decimal_places=2)
    notes = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return f"{self.name} ({self.liability_type})"


class PortfolioSnapshot(models.Model):
    """A daily snapshot of a user's total portfolio value."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="snapshots")
    date = models.DateField()
    total_value = models.DecimalField(max_digits=16, decimal_places=2)
    account_snapshots = models.JSONField(
        default=list,
        help_text="List of {account_id, account_name, value} dicts.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "date")
        ordering = ("date",)

    def __str__(self) -> str:
        return f"Snapshot {self.user.username} @ {self.date} = {self.total_value}"
