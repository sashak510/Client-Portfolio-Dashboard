"""Management command to seed the database with sample data."""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.portfolio.models import Account, Asset, Holding, Transaction


class Command(BaseCommand):
    help = "Seed database with sample users, assets, accounts, holdings, and transactions."

    def handle(self, *args, **options) -> None:
        self.stdout.write("Seeding database...")

        # Users
        admin, _ = User.objects.get_or_create(
            username="admin",
            defaults={"is_staff": True, "is_superuser": True, "email": "admin@example.com"},
        )
        if _:
            admin.set_password("admin")
            admin.save()
            self.stdout.write("  Created superuser: admin/admin")

        user, _ = User.objects.get_or_create(
            username="user1",
            defaults={"email": "user1@example.com"},
        )
        if _:
            user.set_password("testpass123")
            user.save()
            self.stdout.write("  Created user: user1/testpass123")

        # Assets
        aapl, _ = Asset.objects.get_or_create(
            symbol="AAPL",
            defaults={
                "name": "Apple Inc.",
                "asset_type": Asset.AssetType.EQUITY,
                "currency": "USD",
                "last_price": Decimal("178.50"),
                "price_updated_at": timezone.now(),
            },
        )
        hsba, _ = Asset.objects.get_or_create(
            symbol="HSBA.L",
            defaults={
                "name": "HSBC Holdings",
                "asset_type": Asset.AssetType.EQUITY,
                "currency": "GBP",
                "last_price": Decimal("780.00"),
                "price_updated_at": timezone.now(),
            },
        )
        isf, _ = Asset.objects.get_or_create(
            symbol="ISF.L",
            defaults={
                "name": "iShares Core FTSE 100 UCITS ETF",
                "asset_type": Asset.AssetType.EQUITY,
                "currency": "GBP",
                "last_price": Decimal("842.00"),
                "price_updated_at": timezone.now(),
            },
        )
        bond, _ = Asset.objects.get_or_create(
            symbol="UK-GILT-10Y",
            defaults={
                "name": "UK Government Gilt 10-Year",
                "asset_type": Asset.AssetType.BOND,
                "currency": "GBP",
                "face_value": Decimal("100.00"),
                "coupon_rate": Decimal("0.0425"),
                "maturity_date": timezone.now().date() + timedelta(days=3650),
            },
        )
        cash, _ = Asset.objects.get_or_create(
            symbol="GBP-CASH",
            defaults={
                "name": "British Pound Cash",
                "asset_type": Asset.AssetType.CASH,
                "currency": "GBP",
            },
        )

        self.stdout.write("  Assets seeded.")

        # Accounts
        acct1, _ = Account.objects.get_or_create(
            owner=user,
            account_name="Vanguard ISA",
            defaults={
                "account_type": Account.AccountType.ISA,
                "provider": "Vanguard",
            },
        )
        acct2, _ = Account.objects.get_or_create(
            owner=user,
            account_name="AJ Bell SIPP",
            defaults={
                "account_type": Account.AccountType.SIPP,
                "provider": "AJ Bell",
            },
        )
        acct3, _ = Account.objects.get_or_create(
            owner=user,
            account_name="Trading 212 GIA",
            defaults={
                "account_type": Account.AccountType.GIA,
                "provider": "Trading 212",
            },
        )

        self.stdout.write("  Accounts seeded.")

        # Holdings
        holdings_data = [
            (acct1, aapl,  Decimal("50.0000"),    Decimal("145.0000")),
            (acct1, hsba,  Decimal("500.0000"),   Decimal("650.0000")),
            (acct1, bond,  Decimal("100.0000"),   Decimal("98.0000")),
            (acct1, cash,  Decimal("15000.0000"), Decimal("1.0000")),
            (acct2, isf,   Decimal("25.0000"),    Decimal("790.0000")),
            (acct2, aapl,  Decimal("100.0000"),   Decimal("150.0000")),
            (acct2, cash,  Decimal("8000.0000"),  Decimal("1.0000")),
            (acct3, hsba,  Decimal("400.0000"),   Decimal("620.0000")),
            (acct3, bond,  Decimal("200.0000"),   Decimal("99.0000")),
            (acct3, isf,   Decimal("15.0000"),    Decimal("810.0000")),
        ]
        for account, asset, qty, cost in holdings_data:
            Holding.objects.get_or_create(
                account=account,
                asset=asset,
                defaults={"quantity": qty, "average_cost": cost},
            )

        self.stdout.write("  Holdings seeded.")

        # Transactions
        now = timezone.now()
        transactions_data = [
            (acct1, aapl, "buy",     Decimal("50.0000"),    Decimal("145.0000"), now - timedelta(days=150)),
            (acct1, hsba, "buy",     Decimal("500.0000"),   Decimal("650.0000"), now - timedelta(days=120)),
            (acct1, bond, "buy",     Decimal("100.0000"),   Decimal("98.0000"),  now - timedelta(days=100)),
            (acct1, cash, "deposit", Decimal("15000.0000"), Decimal("1.0000"),   now - timedelta(days=90)),
            (acct2, isf,  "buy",     Decimal("25.0000"),    Decimal("790.0000"), now - timedelta(days=140)),
            (acct2, aapl, "buy",     Decimal("120.0000"),   Decimal("148.0000"), now - timedelta(days=130)),
            (acct2, aapl, "sell",    Decimal("20.0000"),    Decimal("172.0000"), now - timedelta(days=45)),
            (acct2, cash, "deposit", Decimal("8000.0000"),  Decimal("1.0000"),   now - timedelta(days=80)),
            (acct3, hsba, "buy",     Decimal("400.0000"),   Decimal("620.0000"), now - timedelta(days=110)),
            (acct3, bond, "buy",     Decimal("200.0000"),   Decimal("99.0000"),  now - timedelta(days=95)),
            (acct3, isf,  "buy",     Decimal("15.0000"),    Decimal("810.0000"), now - timedelta(days=70)),
            (acct3, hsba, "sell",    Decimal("50.0000"),    Decimal("740.0000"), now - timedelta(days=20)),
            (acct3, hsba, "buy",     Decimal("50.0000"),    Decimal("720.0000"), now - timedelta(days=10)),
        ]
        for account, asset, txn_type, qty, price, executed in transactions_data:
            Transaction.objects.get_or_create(
                account=account,
                asset=asset,
                transaction_type=txn_type,
                executed_at=executed,
                defaults={
                    "quantity": qty,
                    "price": price,
                    "total_value": qty * price,
                },
            )

        self.stdout.write("  Transactions seeded.")
        self.stdout.write(self.style.SUCCESS("Database seeding complete!"))
