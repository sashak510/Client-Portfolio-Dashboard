"""Tests for CSV import, watchlist, and currency conversion features."""

import io
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient

from apps.portfolio.models import (
    Account,
    Asset,
    ExchangeRate,
    Holding,
    Transaction,
    WatchlistItem,
)
from apps.portfolio.services import PricingService


@pytest.fixture
def user(db) -> User:
    return User.objects.create_user(username="testuser", password="pass123")


@pytest.fixture
def other_user(db) -> User:
    return User.objects.create_user(username="other", password="pass456")


@pytest.fixture
def api_client(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def account_obj(user: User) -> Account:
    return Account.objects.create(
        owner=user,
        account_name="Test ISA",
        account_type=Account.AccountType.ISA,
    )


@pytest.fixture
def gbp_asset(db) -> Asset:
    return Asset.objects.create(
        symbol="HSBA.L",
        name="HSBC Holdings",
        asset_type=Asset.AssetType.EQUITY,
        currency="GBP",
        last_price=Decimal("780.00"),
        price_updated_at=timezone.now(),
    )


@pytest.fixture
def usd_asset(db) -> Asset:
    return Asset.objects.create(
        symbol="AAPL",
        name="Apple Inc.",
        asset_type=Asset.AssetType.EQUITY,
        currency="USD",
        last_price=Decimal("178.50"),
        price_updated_at=timezone.now(),
    )


# ── Exchange Rate Tests ─────────────────────────────────────────────────


@pytest.mark.django_db
class TestExchangeRate:
    def test_same_currency_returns_one(self):
        rate = ExchangeRate.get_rate("GBP", "GBP")
        assert rate == Decimal("1")

    def test_fallback_rates(self):
        rate = ExchangeRate.get_rate("USD", "GBP")
        assert rate == Decimal("0.79")

    def test_stored_rate_overrides_fallback(self, db):
        ExchangeRate.objects.create(
            from_currency="USD", to_currency="GBP", rate=Decimal("0.80")
        )
        rate = ExchangeRate.get_rate("USD", "GBP")
        assert rate == Decimal("0.80")

    def test_unknown_currency_returns_one(self):
        rate = ExchangeRate.get_rate("JPY", "GBP")
        assert rate == Decimal("1")


# ── Currency Conversion in Portfolio Summary ────────────────────────────


@pytest.mark.django_db
class TestCurrencyConversion:
    def test_portfolio_summary_converts_usd_to_gbp(
        self, api_client, account_obj, usd_asset
    ):
        Holding.objects.create(
            account=account_obj,
            asset=usd_asset,
            quantity=Decimal("10"),
            average_cost=Decimal("150.00"),
        )
        response = api_client.get(
            f"/api/accounts/{account_obj.id}/portfolio-summary/"
        )
        assert response.status_code == 200
        # 10 * 178.50 = 1785 USD, * 0.79 = 1410.15 GBP
        total = Decimal(response.data["total_value"])
        assert total == Decimal("1410.15")

    def test_portfolio_summary_gbp_not_converted(
        self, api_client, account_obj, gbp_asset
    ):
        Holding.objects.create(
            account=account_obj,
            asset=gbp_asset,
            quantity=Decimal("10"),
            average_cost=Decimal("700.00"),
        )
        response = api_client.get(
            f"/api/accounts/{account_obj.id}/portfolio-summary/"
        )
        assert response.status_code == 200
        # 10 * 780 = 7800 GBP, rate 1.0
        total = Decimal(response.data["total_value"])
        assert total == Decimal("7800.00")

    def test_asset_serializer_includes_currency(self, api_client, usd_asset):
        response = api_client.get(f"/api/assets/{usd_asset.id}/")
        assert response.status_code == 200
        assert response.data["currency"] == "USD"


# ── CSV Import Tests ────────────────────────────────────────────────────


def make_csv(rows):
    """Build an in-memory CSV file from a list of dicts."""
    header = "symbol,quantity,price,date,type,account_id"
    lines = [header]
    for r in rows:
        lines.append(",".join(str(r[k]) for k in ["symbol", "quantity", "price", "date", "type", "account_id"]))
    content = "\n".join(lines)
    return io.BytesIO(content.encode("utf-8"))


@pytest.mark.django_db
class TestCSVImport:
    def test_valid_import(self, api_client, account_obj, gbp_asset):
        csv_file = make_csv([
            {"symbol": "HSBA.L", "quantity": "10", "price": "780.00", "date": "2026-01-15", "type": "buy", "account_id": account_obj.id},
        ])
        response = api_client.post(
            "/api/import/",
            {"file": csv_file},
            format="multipart",
        )
        assert response.status_code == 200
        assert response.data["imported"] == 1
        assert response.data["skipped"] == 0
        assert Transaction.objects.filter(account=account_obj).count() == 1
        assert Holding.objects.filter(account=account_obj, asset=gbp_asset).exists()

    def test_missing_file(self, api_client):
        response = api_client.post("/api/import/", {}, format="multipart")
        assert response.status_code == 400

    def test_missing_columns(self, api_client):
        csv_file = io.BytesIO(b"symbol,quantity\nAAPL,10\n")
        response = api_client.post(
            "/api/import/",
            {"file": csv_file},
            format="multipart",
        )
        assert response.status_code == 400
        assert "Missing required columns" in response.data["errors"][0]

    def test_empty_csv(self, api_client):
        csv_file = io.BytesIO(b"")
        response = api_client.post(
            "/api/import/",
            {"file": csv_file},
            format="multipart",
        )
        assert response.status_code == 400

    def test_invalid_rows_skipped(self, api_client, account_obj):
        csv_file = make_csv([
            {"symbol": "AAPL", "quantity": "abc", "price": "178.50", "date": "2026-01-15", "type": "buy", "account_id": account_obj.id},
            {"symbol": "AAPL", "quantity": "10", "price": "178.50", "date": "bad-date", "type": "buy", "account_id": account_obj.id},
            {"symbol": "AAPL", "quantity": "10", "price": "178.50", "date": "2026-01-15", "type": "hold", "account_id": account_obj.id},
        ])
        response = api_client.post(
            "/api/import/",
            {"file": csv_file},
            format="multipart",
        )
        assert response.status_code == 200
        assert response.data["imported"] == 0
        assert response.data["skipped"] == 3
        assert len(response.data["errors"]) == 3

    def test_sell_without_holding_skipped(self, api_client, account_obj, gbp_asset):
        csv_file = make_csv([
            {"symbol": "HSBA.L", "quantity": "10", "price": "780.00", "date": "2026-01-15", "type": "sell", "account_id": account_obj.id},
        ])
        response = api_client.post(
            "/api/import/",
            {"file": csv_file},
            format="multipart",
        )
        assert response.status_code == 200
        assert response.data["skipped"] == 1

    def test_import_wrong_account(self, api_client, other_user):
        other_account = Account.objects.create(
            owner=other_user,
            account_name="Other ISA",
        )
        csv_file = make_csv([
            {"symbol": "AAPL", "quantity": "10", "price": "178.50", "date": "2026-01-15", "type": "buy", "account_id": other_account.id},
        ])
        response = api_client.post(
            "/api/import/",
            {"file": csv_file},
            format="multipart",
        )
        assert response.status_code == 200
        assert response.data["skipped"] == 1
        assert "not found or not owned" in response.data["errors"][0]


# ── Broker Preset Tests ──────────────────────────────────────────────────

T212_HEADER = (
    "Action,Time,ISIN,Ticker,Name,No. of shares,Price / share,"
    "Currency (Price / share),Exchange rate,Result,Currency (Result),"
    "Total,Currency (Total),Withholding tax,Currency (Withholding tax),"
    "Charge amount (EUR),Currency (Charge amount (EUR)),Transaction ID,Notes"
)


def make_t212_csv(rows):
    """Build a Trading 212 CSV from minimal row dicts."""
    lines = [T212_HEADER]
    for r in rows:
        # Fill optional columns with empty strings
        lines.append(
            f"{r['action']},{r['time']},US0000000000,{r['ticker']},Test Inc.,"
            f"{r['shares']},{r['price']},USD,1.00,,,{r.get('total', '')},USD,,,,,,TX001,"
        )
    return io.BytesIO("\n".join(lines).encode("utf-8"))


@pytest.mark.django_db
class TestTrading212Import:
    def test_buy_row_imported(self, api_client, account_obj, gbp_asset):
        csv_file = make_t212_csv([
            {"action": "Market buy", "time": "2024-01-15 09:30:00",
             "ticker": "HSBA.L", "shares": "10", "price": "780.00"},
        ])
        response = api_client.post(
            "/api/import/",
            {"file": csv_file, "broker": "trading212", "account_id": str(account_obj.id)},
            format="multipart",
        )
        assert response.status_code == 200
        assert response.data["imported"] == 1
        assert response.data["skipped"] == 0
        assert Transaction.objects.filter(account=account_obj).count() == 1

    def test_sell_row_type_parsed(self, api_client, account_obj, gbp_asset):
        # First create a holding so the sell can proceed
        Holding.objects.create(
            account=account_obj, asset=gbp_asset,
            quantity=Decimal("20"), average_cost=Decimal("780.00"),
        )
        csv_file = make_t212_csv([
            {"action": "Market sell", "time": "2024-02-10 14:45:00",
             "ticker": "HSBA.L", "shares": "5", "price": "800.00"},
        ])
        response = api_client.post(
            "/api/import/",
            {"file": csv_file, "broker": "trading212", "account_id": str(account_obj.id)},
            format="multipart",
        )
        assert response.status_code == 200
        assert response.data["imported"] == 1

    def test_unknown_action_skipped(self, api_client, account_obj):
        csv_file = make_t212_csv([
            {"action": "Dividend", "time": "2024-03-01 00:00:00",
             "ticker": "AAPL", "shares": "0", "price": "0"},
        ])
        response = api_client.post(
            "/api/import/",
            {"file": csv_file, "broker": "trading212", "account_id": str(account_obj.id)},
            format="multipart",
        )
        assert response.status_code == 200
        assert response.data["skipped"] == 1
        assert "unrecognised Action" in response.data["errors"][0]

    def test_date_extracted_from_time_column(self, api_client, account_obj, gbp_asset):
        csv_file = make_t212_csv([
            {"action": "Market buy", "time": "2024-06-20 11:00:00",
             "ticker": "HSBA.L", "shares": "2", "price": "790.00"},
        ])
        response = api_client.post(
            "/api/import/",
            {"file": csv_file, "broker": "trading212", "account_id": str(account_obj.id)},
            format="multipart",
        )
        assert response.status_code == 200
        assert response.data["imported"] == 1
        tx = Transaction.objects.filter(account=account_obj).first()
        assert tx.executed_at.date().isoformat() == "2024-06-20"


@pytest.mark.django_db
class TestCSVSample:
    def test_generic_sample_download(self, api_client):
        response = api_client.get("/api/import/sample/generic/")
        assert response.status_code == 200
        assert "symbol" in response.content.decode()

    def test_trading212_sample_download(self, api_client):
        response = api_client.get("/api/import/sample/trading212/")
        assert response.status_code == 200
        assert "Action" in response.content.decode()

    def test_unknown_broker_404(self, api_client):
        response = api_client.get("/api/import/sample/fakebroker/")
        assert response.status_code == 404

    def test_coming_soon_sample_download(self, api_client):
        response = api_client.get("/api/import/sample/vanguard_uk/")
        assert response.status_code == 200
        assert "coming soon" in response.content.decode().lower()


# ── Watchlist Tests ─────────────────────────────────────────────────────


@pytest.mark.django_db
class TestWatchlistAPI:
    def test_create_watchlist_item(self, api_client, gbp_asset):
        response = api_client.post(
            "/api/watchlist/",
            {"asset": gbp_asset.id, "target_price": "800.00", "notes": "Watching HSBC"},
        )
        assert response.status_code == 201
        assert response.data["target_price"] == "800.0000"
        assert response.data["asset_detail"]["symbol"] == "HSBA.L"

    def test_list_watchlist(self, api_client, gbp_asset, user):
        WatchlistItem.objects.create(
            user=user, asset=gbp_asset, target_price=Decimal("800.00")
        )
        response = api_client.get("/api/watchlist/")
        assert response.status_code == 200
        results = response.data["results"] if "results" in response.data else response.data
        assert len(results) == 1

    def test_delete_watchlist_item(self, api_client, gbp_asset, user):
        item = WatchlistItem.objects.create(
            user=user, asset=gbp_asset, target_price=Decimal("800.00")
        )
        response = api_client.delete(f"/api/watchlist/{item.id}/")
        assert response.status_code == 204
        assert WatchlistItem.objects.count() == 0

    def test_user_isolation(self, api_client, gbp_asset, other_user):
        WatchlistItem.objects.create(
            user=other_user, asset=gbp_asset, target_price=Decimal("800.00")
        )
        response = api_client.get("/api/watchlist/")
        results = response.data["results"] if "results" in response.data else response.data
        assert len(results) == 0

    def test_unique_user_asset(self, user, gbp_asset):
        WatchlistItem.objects.create(user=user, asset=gbp_asset)
        with pytest.raises(Exception):
            WatchlistItem.objects.create(user=user, asset=gbp_asset)
