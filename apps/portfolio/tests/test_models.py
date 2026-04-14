"""Tests for portfolio models."""

from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.utils import timezone

from apps.portfolio.models import Asset, Client, Holding, Transaction


@pytest.fixture
def user(db) -> User:
    return User.objects.create_user(username="testadvisor", password="pass123")


@pytest.fixture
def client_obj(user: User) -> Client:
    return Client.objects.create(
        owner=user,
        first_name="Test",
        last_name="Client",
        email="test@example.com",
    )


@pytest.fixture
def equity_asset(db) -> Asset:
    return Asset.objects.create(
        symbol="AAPL",
        name="Apple Inc.",
        asset_type=Asset.AssetType.EQUITY,
        last_price=Decimal("175.00"),
        price_updated_at=timezone.now(),
    )


@pytest.mark.django_db
class TestClientModel:
    def test_str_representation(self, client_obj: Client) -> None:
        assert str(client_obj) == "Test Client"


@pytest.mark.django_db
class TestHoldingModel:
    def test_unique_together_constraint(
        self, client_obj: Client, equity_asset: Asset
    ) -> None:
        Holding.objects.create(
            client=client_obj,
            asset=equity_asset,
            quantity=Decimal("10"),
            average_cost=Decimal("150.00"),
        )
        with pytest.raises(IntegrityError):
            Holding.objects.create(
                client=client_obj,
                asset=equity_asset,
                quantity=Decimal("5"),
                average_cost=Decimal("160.00"),
            )


@pytest.mark.django_db
class TestTransactionModel:
    def test_total_value_stored_correctly(
        self, client_obj: Client, equity_asset: Asset
    ) -> None:
        qty = Decimal("10.0000")
        price = Decimal("175.0000")
        txn = Transaction.objects.create(
            client=client_obj,
            asset=equity_asset,
            transaction_type=Transaction.TransactionType.BUY,
            quantity=qty,
            price=price,
            total_value=qty * price,
            executed_at=timezone.now(),
        )
        assert txn.total_value == Decimal("1750.00")
