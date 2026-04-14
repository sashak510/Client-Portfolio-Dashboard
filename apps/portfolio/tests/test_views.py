"""Tests for portfolio API views."""

from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient

from apps.portfolio.models import Asset, Client, Holding, Transaction


@pytest.fixture
def user(db) -> User:
    return User.objects.create_user(username="advisor1", password="pass123")


@pytest.fixture
def other_user(db) -> User:
    return User.objects.create_user(username="advisor2", password="pass456")


@pytest.fixture
def api_client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def equity_asset(db) -> Asset:
    return Asset.objects.create(
        symbol="AAPL",
        name="Apple Inc.",
        asset_type=Asset.AssetType.EQUITY,
        last_price=Decimal("178.50"),
        price_updated_at=timezone.now(),
    )


@pytest.fixture
def cash_asset(db) -> Asset:
    return Asset.objects.create(
        symbol="USD-CASH",
        name="US Dollar Cash",
        asset_type=Asset.AssetType.CASH,
    )


@pytest.fixture
def bond_asset(db) -> Asset:
    return Asset.objects.create(
        symbol="US-BOND",
        name="US Treasury",
        asset_type=Asset.AssetType.BOND,
        face_value=Decimal("1000.00"),
    )


@pytest.fixture
def client_obj(user: User) -> Client:
    return Client.objects.create(
        owner=user,
        first_name="John",
        last_name="Doe",
        email="john@example.com",
    )


@pytest.mark.django_db
class TestClientCRUD:
    def test_create_client(self, api_client: APIClient) -> None:
        data = {
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "jane@example.com",
        }
        response = api_client.post("/api/clients/", data)
        assert response.status_code == 201
        assert response.data["first_name"] == "Jane"

    def test_list_clients(self, api_client: APIClient, client_obj: Client) -> None:
        response = api_client.get("/api/clients/")
        assert response.status_code == 200
        assert response.data["count"] == 1

    def test_retrieve_client(self, api_client: APIClient, client_obj: Client) -> None:
        response = api_client.get(f"/api/clients/{client_obj.id}/")
        assert response.status_code == 200
        assert response.data["first_name"] == "John"

    def test_update_client(self, api_client: APIClient, client_obj: Client) -> None:
        response = api_client.patch(
            f"/api/clients/{client_obj.id}/",
            {"phone": "+1234567890"},
        )
        assert response.status_code == 200
        assert response.data["phone"] == "+1234567890"

    def test_delete_client(self, api_client: APIClient, client_obj: Client) -> None:
        response = api_client.delete(f"/api/clients/{client_obj.id}/")
        assert response.status_code == 204
        assert not Client.objects.filter(id=client_obj.id).exists()

    def test_user_cannot_see_other_users_clients(
        self, other_user: User, api_client: APIClient
    ) -> None:
        Client.objects.create(
            owner=other_user,
            first_name="Other",
            last_name="Client",
            email="other@example.com",
        )
        response = api_client.get("/api/clients/")
        assert response.data["count"] == 0


@pytest.mark.django_db
class TestPortfolioSummary:
    def test_portfolio_summary_structure(
        self,
        api_client: APIClient,
        client_obj: Client,
        equity_asset: Asset,
        cash_asset: Asset,
    ) -> None:
        Holding.objects.create(
            client=client_obj,
            asset=equity_asset,
            quantity=Decimal("10"),
            average_cost=Decimal("150.00"),
        )
        Holding.objects.create(
            client=client_obj,
            asset=cash_asset,
            quantity=Decimal("5000"),
            average_cost=Decimal("1.00"),
        )
        response = api_client.get(f"/api/clients/{client_obj.id}/portfolio-summary/")
        assert response.status_code == 200
        assert "total_value" in response.data
        assert "equity_allocation_pct" in response.data
        assert "bond_allocation_pct" in response.data
        assert "cash_allocation_pct" in response.data
        assert "top_holdings" in response.data
        assert "total_gain_loss" in response.data


@pytest.mark.django_db
class TestTransactionValidation:
    def test_sell_exceeds_holding(
        self,
        api_client: APIClient,
        client_obj: Client,
        equity_asset: Asset,
    ) -> None:
        Holding.objects.create(
            client=client_obj,
            asset=equity_asset,
            quantity=Decimal("10"),
            average_cost=Decimal("150.00"),
        )
        data = {
            "client": client_obj.id,
            "asset": equity_asset.id,
            "transaction_type": "sell",
            "quantity": "20.0000",
            "price": "175.0000",
            "executed_at": timezone.now().isoformat(),
        }
        response = api_client.post("/api/transactions/", data)
        assert response.status_code == 400


@pytest.mark.django_db
class TestTransactionFiltering:
    def test_filter_by_type(
        self,
        api_client: APIClient,
        client_obj: Client,
        equity_asset: Asset,
    ) -> None:
        now = timezone.now()
        Transaction.objects.create(
            client=client_obj,
            asset=equity_asset,
            transaction_type="buy",
            quantity=Decimal("10"),
            price=Decimal("150"),
            total_value=Decimal("1500"),
            executed_at=now,
        )
        Transaction.objects.create(
            client=client_obj,
            asset=equity_asset,
            transaction_type="sell",
            quantity=Decimal("5"),
            price=Decimal("175"),
            total_value=Decimal("875"),
            executed_at=now,
        )
        response = api_client.get("/api/transactions/?transaction_type=buy")
        assert response.status_code == 200
        assert response.data["count"] == 1

    def test_filter_by_date_range(
        self,
        api_client: APIClient,
        client_obj: Client,
        equity_asset: Asset,
    ) -> None:
        from datetime import timedelta

        now = timezone.now()
        Transaction.objects.create(
            client=client_obj,
            asset=equity_asset,
            transaction_type="buy",
            quantity=Decimal("10"),
            price=Decimal("150"),
            total_value=Decimal("1500"),
            executed_at=now - timedelta(days=30),
        )
        Transaction.objects.create(
            client=client_obj,
            asset=equity_asset,
            transaction_type="buy",
            quantity=Decimal("5"),
            price=Decimal("160"),
            total_value=Decimal("800"),
            executed_at=now - timedelta(days=5),
        )
        cutoff = (now - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%S")
        response = api_client.get(f"/api/transactions/?executed_at_after={cutoff}")
        assert response.status_code == 200
        assert response.data["count"] == 1
