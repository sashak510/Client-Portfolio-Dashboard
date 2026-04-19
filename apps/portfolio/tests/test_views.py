"""Tests for portfolio API views."""

from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient

from apps.portfolio.models import Account, Asset, Holding, Transaction


@pytest.fixture
def user(db) -> User:
    return User.objects.create_user(username="user1", password="pass123")


@pytest.fixture
def other_user(db) -> User:
    return User.objects.create_user(username="user2", password="pass456")


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
def account_obj(user: User) -> Account:
    return Account.objects.create(
        owner=user,
        account_name="Vanguard ISA",
        account_type=Account.AccountType.ISA,
        provider="Vanguard",
    )


@pytest.mark.django_db
class TestAccountCRUD:
    def test_create_account(self, api_client: APIClient) -> None:
        data = {
            "account_name": "AJ Bell SIPP",
            "account_type": "sipp",
            "provider": "AJ Bell",
        }
        response = api_client.post("/api/accounts/", data)
        assert response.status_code == 201
        assert response.data["account_name"] == "AJ Bell SIPP"

    def test_list_accounts(self, api_client: APIClient, account_obj: Account) -> None:
        response = api_client.get("/api/accounts/")
        assert response.status_code == 200
        assert response.data["count"] == 1

    def test_retrieve_account(self, api_client: APIClient, account_obj: Account) -> None:
        response = api_client.get(f"/api/accounts/{account_obj.id}/")
        assert response.status_code == 200
        assert response.data["account_name"] == "Vanguard ISA"

    def test_update_account(self, api_client: APIClient, account_obj: Account) -> None:
        response = api_client.patch(
            f"/api/accounts/{account_obj.id}/",
            {"provider": "Vanguard UK"},
        )
        assert response.status_code == 200
        assert response.data["provider"] == "Vanguard UK"

    def test_delete_account(self, api_client: APIClient, account_obj: Account) -> None:
        response = api_client.delete(f"/api/accounts/{account_obj.id}/")
        assert response.status_code == 204
        assert not Account.objects.filter(id=account_obj.id).exists()

    def test_user_cannot_see_other_users_accounts(
        self, other_user: User, api_client: APIClient
    ) -> None:
        Account.objects.create(
            owner=other_user,
            account_name="Other GIA",
            account_type=Account.AccountType.GIA,
        )
        response = api_client.get("/api/accounts/")
        assert response.data["count"] == 0


@pytest.mark.django_db
class TestPortfolioSummary:
    def test_portfolio_summary_structure(
        self,
        api_client: APIClient,
        account_obj: Account,
        equity_asset: Asset,
        cash_asset: Asset,
    ) -> None:
        Holding.objects.create(
            account=account_obj,
            asset=equity_asset,
            quantity=Decimal("10"),
            average_cost=Decimal("150.00"),
        )
        Holding.objects.create(
            account=account_obj,
            asset=cash_asset,
            quantity=Decimal("5000"),
            average_cost=Decimal("1.00"),
        )
        response = api_client.get(f"/api/accounts/{account_obj.id}/portfolio-summary/")
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
        account_obj: Account,
        equity_asset: Asset,
    ) -> None:
        Holding.objects.create(
            account=account_obj,
            asset=equity_asset,
            quantity=Decimal("10"),
            average_cost=Decimal("150.00"),
        )
        data = {
            "account": account_obj.id,
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
        account_obj: Account,
        equity_asset: Asset,
    ) -> None:
        now = timezone.now()
        Transaction.objects.create(
            account=account_obj,
            asset=equity_asset,
            transaction_type="buy",
            quantity=Decimal("10"),
            price=Decimal("150"),
            total_value=Decimal("1500"),
            executed_at=now,
        )
        Transaction.objects.create(
            account=account_obj,
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
        account_obj: Account,
        equity_asset: Asset,
    ) -> None:
        from datetime import timedelta

        now = timezone.now()
        Transaction.objects.create(
            account=account_obj,
            asset=equity_asset,
            transaction_type="buy",
            quantity=Decimal("10"),
            price=Decimal("150"),
            total_value=Decimal("1500"),
            executed_at=now - timedelta(days=30),
        )
        Transaction.objects.create(
            account=account_obj,
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


@pytest.mark.django_db
class TestCSVExport:
    def test_csv_export_holdings_success(
        self,
        api_client: APIClient,
        account_obj: Account,
        equity_asset: Asset,
    ) -> None:
        from unittest.mock import patch

        Holding.objects.create(
            account=account_obj,
            asset=equity_asset,
            quantity=Decimal("10"),
            average_cost=Decimal("150.00"),
        )
        with patch("apps.portfolio.services.yf") as mock_yf:
            mock_ticker = mock_yf.Ticker.return_value
            mock_ticker.fast_info.get.return_value = 178.50
            response = api_client.get(f"/api/accounts/{account_obj.id}/export/?type=holdings")

        assert response.status_code == 200
        assert "text/csv" in response["Content-Type"]
        content = response.content.decode("utf-8")
        first_line = content.splitlines()[0]
        assert "Asset Symbol" in first_line
        assert "Allocation %" in first_line

    def test_csv_export_transactions_success(
        self,
        api_client: APIClient,
        account_obj: Account,
        equity_asset: Asset,
    ) -> None:
        Transaction.objects.create(
            account=account_obj,
            asset=equity_asset,
            transaction_type="buy",
            quantity=Decimal("5"),
            price=Decimal("150.00"),
            total_value=Decimal("750.00"),
            executed_at=timezone.now(),
        )
        response = api_client.get(f"/api/accounts/{account_obj.id}/export/?type=transactions")
        assert response.status_code == 200
        assert "text/csv" in response["Content-Type"]
        content = response.content.decode("utf-8")
        first_line = content.splitlines()[0]
        assert "Date" in first_line
        assert "Asset Symbol" in first_line
        assert "Total Value" in first_line

    def test_csv_export_invalid_type(
        self, api_client: APIClient, account_obj: Account
    ) -> None:
        response = api_client.get(f"/api/accounts/{account_obj.id}/export/?type=invalid")
        assert response.status_code == 400
        assert "Invalid export type" in response.data["detail"]

    def test_csv_export_other_users_account(
        self, api_client: APIClient, other_user: User
    ) -> None:
        other_account = Account.objects.create(
            owner=other_user,
            account_name="Other GIA",
            account_type=Account.AccountType.GIA,
        )
        response = api_client.get(f"/api/accounts/{other_account.id}/export/?type=holdings")
        assert response.status_code == 404


@pytest.mark.django_db
class TestPerformanceEndpoint:
    def test_performance_default_period(
        self,
        api_client: APIClient,
        account_obj: Account,
        equity_asset: Asset,
    ) -> None:
        from unittest.mock import patch

        Holding.objects.create(
            account=account_obj,
            asset=equity_asset,
            quantity=Decimal("10"),
            average_cost=Decimal("150.00"),
        )
        with patch("apps.portfolio.services.yf") as mock_yf:
            mock_ticker = mock_yf.Ticker.return_value
            mock_ticker.fast_info.get.return_value = 178.50
            response = api_client.get(f"/api/accounts/{account_obj.id}/performance/")

        assert response.status_code == 200
        expected_keys = {
            "account_id",
            "account_name",
            "period_days",
            "start_date",
            "end_date",
            "current_value",
            "cost_basis",
            "total_gain_loss",
            "total_return_pct",
            "transactions_in_period",
            "net_invested_in_period",
            "holdings_breakdown",
        }
        assert expected_keys.issubset(response.data.keys())

    def test_performance_custom_period(
        self,
        api_client: APIClient,
        account_obj: Account,
    ) -> None:
        from unittest.mock import patch

        with patch("apps.portfolio.services.yf"):
            response = api_client.get(f"/api/accounts/{account_obj.id}/performance/?period=7")

        assert response.status_code == 200
        assert response.data["period_days"] == 7

    def test_performance_invalid_period(
        self, api_client: APIClient, account_obj: Account
    ) -> None:
        response = api_client.get(f"/api/accounts/{account_obj.id}/performance/?period=15")
        assert response.status_code == 400
        assert "Invalid period" in response.data["detail"]

    def test_performance_other_users_account(
        self, api_client: APIClient, other_user: User
    ) -> None:
        other_account = Account.objects.create(
            owner=other_user,
            account_name="Other SIPP",
            account_type=Account.AccountType.SIPP,
        )
        response = api_client.get(f"/api/accounts/{other_account.id}/performance/")
        assert response.status_code == 404
