"""Tests for TargetAllocation, Dividend, and Holding notes features."""

from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.utils import timezone
from rest_framework.test import APIClient

from apps.portfolio.models import (
    Account,
    Asset,
    Dividend,
    Holding,
    TargetAllocation,
)


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
def bond_asset(db) -> Asset:
    return Asset.objects.create(
        symbol="US-BOND",
        name="US Treasury",
        asset_type=Asset.AssetType.BOND,
        face_value=Decimal("1000.00"),
    )


@pytest.fixture
def cash_asset(db) -> Asset:
    return Asset.objects.create(
        symbol="USD-CASH",
        name="US Dollar Cash",
        asset_type=Asset.AssetType.CASH,
    )


@pytest.fixture
def account_obj(user: User) -> Account:
    return Account.objects.create(
        owner=user,
        account_name="Vanguard ISA",
        account_type=Account.AccountType.ISA,
        provider="Vanguard",
    )


@pytest.fixture
def holding(account_obj: Account, equity_asset: Asset) -> Holding:
    return Holding.objects.create(
        account=account_obj,
        asset=equity_asset,
        quantity=Decimal("10"),
        average_cost=Decimal("150.00"),
    )


# ── TargetAllocation Model Tests ─────────────────────────────────────────


@pytest.mark.django_db
class TestTargetAllocationModel:
    def test_create_target_allocation(self, account_obj: Account) -> None:
        ta = TargetAllocation.objects.create(
            account=account_obj,
            asset_type=Asset.AssetType.EQUITY,
            target_percentage=Decimal("60.00"),
        )
        assert str(ta) == "Vanguard ISA - Equity target 60.00%"

    def test_unique_together_constraint(self, account_obj: Account) -> None:
        TargetAllocation.objects.create(
            account=account_obj,
            asset_type=Asset.AssetType.EQUITY,
            target_percentage=Decimal("60.00"),
        )
        with pytest.raises(IntegrityError):
            TargetAllocation.objects.create(
                account=account_obj,
                asset_type=Asset.AssetType.EQUITY,
                target_percentage=Decimal("70.00"),
            )


# ── TargetAllocation API Tests ───────────────────────────────────────────


@pytest.mark.django_db
class TestTargetAllocationAPI:
    def test_create_target_allocation(
        self, api_client: APIClient, account_obj: Account
    ) -> None:
        data = {
            "account": account_obj.id,
            "asset_type": "equity",
            "target_percentage": "60.00",
        }
        response = api_client.post("/api/target-allocations/", data)
        assert response.status_code == 201
        assert response.data["target_percentage"] == "60.00"

    def test_list_target_allocations(
        self, api_client: APIClient, account_obj: Account
    ) -> None:
        TargetAllocation.objects.create(
            account=account_obj,
            asset_type=Asset.AssetType.EQUITY,
            target_percentage=Decimal("60.00"),
        )
        TargetAllocation.objects.create(
            account=account_obj,
            asset_type=Asset.AssetType.BOND,
            target_percentage=Decimal("30.00"),
        )
        response = api_client.get("/api/target-allocations/")
        assert response.status_code == 200
        assert response.data["count"] == 2

    def test_filter_by_account(
        self, api_client: APIClient, account_obj: Account
    ) -> None:
        TargetAllocation.objects.create(
            account=account_obj,
            asset_type=Asset.AssetType.EQUITY,
            target_percentage=Decimal("60.00"),
        )
        response = api_client.get(
            f"/api/target-allocations/?account={account_obj.id}"
        )
        assert response.status_code == 200
        assert response.data["count"] == 1

    def test_update_target_allocation(
        self, api_client: APIClient, account_obj: Account
    ) -> None:
        ta = TargetAllocation.objects.create(
            account=account_obj,
            asset_type=Asset.AssetType.EQUITY,
            target_percentage=Decimal("60.00"),
        )
        response = api_client.patch(
            f"/api/target-allocations/{ta.id}/",
            {"target_percentage": "50.00"},
        )
        assert response.status_code == 200
        assert response.data["target_percentage"] == "50.00"

    def test_delete_target_allocation(
        self, api_client: APIClient, account_obj: Account
    ) -> None:
        ta = TargetAllocation.objects.create(
            account=account_obj,
            asset_type=Asset.AssetType.EQUITY,
            target_percentage=Decimal("60.00"),
        )
        response = api_client.delete(f"/api/target-allocations/{ta.id}/")
        assert response.status_code == 204

    def test_user_cannot_see_other_users_targets(
        self, api_client: APIClient, other_user: User
    ) -> None:
        other_account = Account.objects.create(
            owner=other_user,
            account_name="Other GIA",
            account_type=Account.AccountType.GIA,
        )
        TargetAllocation.objects.create(
            account=other_account,
            asset_type=Asset.AssetType.EQUITY,
            target_percentage=Decimal("50.00"),
        )
        response = api_client.get("/api/target-allocations/")
        assert response.data["count"] == 0


# ── Dividend Model Tests ─────────────────────────────────────────────────


@pytest.mark.django_db
class TestDividendModel:
    def test_create_dividend(self, holding: Holding) -> None:
        div = Dividend.objects.create(
            holding=holding,
            amount=Decimal("25.00"),
            per_share_amount=Decimal("2.5000"),
            ex_date="2026-03-15",
            payment_date="2026-04-01",
        )
        assert "Dividend" in str(div)
        assert "25.00" in str(div)

    def test_dividend_ordering(self, holding: Holding) -> None:
        Dividend.objects.create(
            holding=holding,
            amount=Decimal("10.00"),
            per_share_amount=Decimal("1.0000"),
            ex_date="2026-01-15",
            payment_date="2026-02-01",
        )
        Dividend.objects.create(
            holding=holding,
            amount=Decimal("20.00"),
            per_share_amount=Decimal("2.0000"),
            ex_date="2026-03-15",
            payment_date="2026-04-01",
        )
        divs = list(Dividend.objects.all())
        assert divs[0].amount == Decimal("20.00")  # most recent first


# ── Dividend API Tests ───────────────────────────────────────────────────


@pytest.mark.django_db
class TestDividendAPI:
    def test_create_dividend(
        self, api_client: APIClient, holding: Holding
    ) -> None:
        data = {
            "holding": holding.id,
            "amount": "25.00",
            "per_share_amount": "2.5000",
            "ex_date": "2026-03-15",
            "payment_date": "2026-04-01",
        }
        response = api_client.post("/api/dividends/", data)
        assert response.status_code == 201
        assert response.data["amount"] == "25.00"
        assert response.data["holding_detail"]["symbol"] == "AAPL"

    def test_list_dividends(
        self, api_client: APIClient, holding: Holding
    ) -> None:
        Dividend.objects.create(
            holding=holding,
            amount=Decimal("25.00"),
            per_share_amount=Decimal("2.5000"),
            ex_date="2026-03-15",
            payment_date="2026-04-01",
        )
        response = api_client.get("/api/dividends/")
        assert response.status_code == 200
        assert response.data["count"] == 1

    def test_delete_dividend(
        self, api_client: APIClient, holding: Holding
    ) -> None:
        div = Dividend.objects.create(
            holding=holding,
            amount=Decimal("25.00"),
            per_share_amount=Decimal("2.5000"),
            ex_date="2026-03-15",
            payment_date="2026-04-01",
        )
        response = api_client.delete(f"/api/dividends/{div.id}/")
        assert response.status_code == 204

    def test_user_cannot_see_other_users_dividends(
        self, api_client: APIClient, other_user: User, equity_asset: Asset
    ) -> None:
        other_account = Account.objects.create(
            owner=other_user,
            account_name="Other GIA",
            account_type=Account.AccountType.GIA,
        )
        other_holding = Holding.objects.create(
            account=other_account,
            asset=equity_asset,
            quantity=Decimal("5"),
            average_cost=Decimal("160.00"),
        )
        Dividend.objects.create(
            holding=other_holding,
            amount=Decimal("12.50"),
            per_share_amount=Decimal("2.5000"),
            ex_date="2026-03-15",
            payment_date="2026-04-01",
        )
        response = api_client.get("/api/dividends/")
        assert response.data["count"] == 0


# ── Holding Notes Tests ──────────────────────────────────────────────────


@pytest.mark.django_db
class TestHoldingNotes:
    def test_holding_has_notes_field(self, holding: Holding) -> None:
        assert holding.notes == ""

    def test_patch_notes(
        self, api_client: APIClient, holding: Holding
    ) -> None:
        response = api_client.patch(
            f"/api/holdings/{holding.id}/",
            {"notes": "Long-term hold, core position"},
        )
        assert response.status_code == 200
        assert response.data["notes"] == "Long-term hold, core position"

    def test_notes_in_listing(
        self, api_client: APIClient, holding: Holding
    ) -> None:
        holding.notes = "Some note"
        holding.save()
        response = api_client.get("/api/holdings/")
        assert response.status_code == 200
        results = response.data["results"]
        assert len(results) == 1
        assert results[0]["notes"] == "Some note"


# ── Portfolio Summary with Dividends ─────────────────────────────────────


@pytest.mark.django_db
class TestPortfolioSummaryWithDividends:
    def test_summary_includes_total_dividends(
        self,
        api_client: APIClient,
        account_obj: Account,
        holding: Holding,
    ) -> None:
        Dividend.objects.create(
            holding=holding,
            amount=Decimal("25.00"),
            per_share_amount=Decimal("2.5000"),
            ex_date="2026-03-15",
            payment_date="2026-04-01",
        )
        Dividend.objects.create(
            holding=holding,
            amount=Decimal("30.00"),
            per_share_amount=Decimal("3.0000"),
            ex_date="2026-01-15",
            payment_date="2026-02-01",
        )
        response = api_client.get(
            f"/api/accounts/{account_obj.id}/portfolio-summary/"
        )
        assert response.status_code == 200
        assert "total_dividends" in response.data
        assert Decimal(response.data["total_dividends"]) == Decimal("55.00")
