"""Management command to seed the database with sample data."""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.portfolio.models import Asset, Client, Holding, Transaction


class Command(BaseCommand):
    help = "Seed database with sample users, assets, clients, holdings, and transactions."

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

        advisor, _ = User.objects.get_or_create(
            username="advisor1",
            defaults={"email": "advisor1@example.com"},
        )
        if _:
            advisor.set_password("testpass123")
            advisor.save()
            self.stdout.write("  Created user: advisor1/testpass123")

        # Assets
        aapl, _ = Asset.objects.get_or_create(
            symbol="AAPL",
            defaults={
                "name": "Apple Inc.",
                "asset_type": Asset.AssetType.EQUITY,
                "last_price": Decimal("178.50"),
                "price_updated_at": timezone.now(),
            },
        )
        msft, _ = Asset.objects.get_or_create(
            symbol="MSFT",
            defaults={
                "name": "Microsoft Corporation",
                "asset_type": Asset.AssetType.EQUITY,
                "last_price": Decimal("415.20"),
                "price_updated_at": timezone.now(),
            },
        )
        voo, _ = Asset.objects.get_or_create(
            symbol="VOO",
            defaults={
                "name": "Vanguard S&P 500 ETF",
                "asset_type": Asset.AssetType.EQUITY,
                "last_price": Decimal("502.30"),
                "price_updated_at": timezone.now(),
            },
        )
        bond, _ = Asset.objects.get_or_create(
            symbol="US-TBOND-10Y",
            defaults={
                "name": "US Treasury Bond 10-Year",
                "asset_type": Asset.AssetType.BOND,
                "face_value": Decimal("1000.00"),
                "coupon_rate": Decimal("0.0425"),
                "maturity_date": timezone.now().date() + timedelta(days=3650),
            },
        )
        cash, _ = Asset.objects.get_or_create(
            symbol="GBP-CASH",
            defaults={
                "name": "British Pound Cash",
                "asset_type": Asset.AssetType.CASH,
            },
        )

        self.stdout.write("  Assets seeded.")

        # Clients
        client1, _ = Client.objects.get_or_create(
            email="john.doe@example.com",
            defaults={
                "owner": advisor,
                "first_name": "John",
                "last_name": "Doe",
                "phone": "+44 7700 900001",
            },
        )
        client2, _ = Client.objects.get_or_create(
            email="jane.smith@example.com",
            defaults={
                "owner": advisor,
                "first_name": "Jane",
                "last_name": "Smith",
                "phone": "+44 7700 900002",
            },
        )
        client3, _ = Client.objects.get_or_create(
            email="bob.wilson@example.com",
            defaults={
                "owner": advisor,
                "first_name": "Bob",
                "last_name": "Wilson",
                "phone": "+44 7700 900003",
            },
        )

        self.stdout.write("  Clients seeded.")

        # Holdings
        holdings_data = [
            (client1, aapl, Decimal("50.0000"), Decimal("145.0000")),
            (client1, msft, Decimal("30.0000"), Decimal("380.0000")),
            (client1, bond, Decimal("10.0000"), Decimal("980.0000")),
            (client1, cash, Decimal("15000.0000"), Decimal("1.0000")),
            (client2, voo, Decimal("25.0000"), Decimal("470.0000")),
            (client2, aapl, Decimal("100.0000"), Decimal("150.0000")),
            (client2, cash, Decimal("8000.0000"), Decimal("1.0000")),
            (client3, msft, Decimal("40.0000"), Decimal("390.0000")),
            (client3, bond, Decimal("20.0000"), Decimal("990.0000")),
            (client3, voo, Decimal("15.0000"), Decimal("480.0000")),
        ]
        for client, asset, qty, cost in holdings_data:
            Holding.objects.get_or_create(
                client=client,
                asset=asset,
                defaults={"quantity": qty, "average_cost": cost},
            )

        self.stdout.write("  Holdings seeded.")

        # Transactions
        now = timezone.now()
        transactions_data = [
            (client1, aapl, "buy", Decimal("50.0000"), Decimal("145.0000"), now - timedelta(days=150)),
            (client1, msft, "buy", Decimal("30.0000"), Decimal("380.0000"), now - timedelta(days=120)),
            (client1, bond, "buy", Decimal("10.0000"), Decimal("980.0000"), now - timedelta(days=100)),
            (client1, cash, "deposit", Decimal("15000.0000"), Decimal("1.0000"), now - timedelta(days=90)),
            (client2, voo, "buy", Decimal("25.0000"), Decimal("470.0000"), now - timedelta(days=140)),
            (client2, aapl, "buy", Decimal("120.0000"), Decimal("148.0000"), now - timedelta(days=130)),
            (client2, aapl, "sell", Decimal("20.0000"), Decimal("172.0000"), now - timedelta(days=45)),
            (client2, cash, "deposit", Decimal("8000.0000"), Decimal("1.0000"), now - timedelta(days=80)),
            (client3, msft, "buy", Decimal("40.0000"), Decimal("390.0000"), now - timedelta(days=110)),
            (client3, bond, "buy", Decimal("20.0000"), Decimal("990.0000"), now - timedelta(days=95)),
            (client3, voo, "buy", Decimal("15.0000"), Decimal("480.0000"), now - timedelta(days=70)),
            (client3, msft, "sell", Decimal("5.0000"), Decimal("410.0000"), now - timedelta(days=20)),
            (client3, msft, "buy", Decimal("5.0000"), Decimal("405.0000"), now - timedelta(days=10)),
        ]
        for client, asset, txn_type, qty, price, executed in transactions_data:
            Transaction.objects.get_or_create(
                client=client,
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
