"""Tests for PricingService."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth.models import User
from django.utils import timezone

from apps.portfolio.models import Asset, Client, Holding
from apps.portfolio.services import PricingService


@pytest.fixture
def user(db) -> User:
    return User.objects.create_user(username="testadvisor", password="pass123")


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
def equity_asset(db) -> Asset:
    return Asset.objects.create(
        symbol="AAPL",
        name="Apple Inc.",
        asset_type=Asset.AssetType.EQUITY,
    )


@pytest.fixture
def client_obj(user: User) -> Client:
    return Client.objects.create(
        owner=user,
        first_name="Test",
        last_name="Client",
        email="test@example.com",
    )


@pytest.mark.django_db
class TestPricingService:
    def test_cash_returns_one(self, cash_asset: Asset) -> None:
        assert PricingService.get_current_price(cash_asset) == Decimal("1.0")

    def test_bond_returns_face_value(self, bond_asset: Asset) -> None:
        assert PricingService.get_current_price(bond_asset) == Decimal("1000.00")

    @patch("apps.portfolio.services.yf")
    def test_equity_fetches_from_yfinance(
        self, mock_yf: MagicMock, equity_asset: Asset
    ) -> None:
        mock_ticker = MagicMock()
        mock_ticker.fast_info.get.return_value = 185.50
        mock_yf.Ticker.return_value = mock_ticker

        price = PricingService.get_current_price(equity_asset)
        assert price == Decimal("185.5")
        mock_yf.Ticker.assert_called_once_with("AAPL")

    @patch("apps.portfolio.services.yf")
    def test_equity_uses_cache_when_fresh(
        self, mock_yf: MagicMock, equity_asset: Asset
    ) -> None:
        equity_asset.last_price = Decimal("180.00")
        equity_asset.price_updated_at = timezone.now()
        equity_asset.save()

        price = PricingService.get_current_price(equity_asset)
        assert price == Decimal("180.00")
        mock_yf.Ticker.assert_not_called()

    @patch("apps.portfolio.services.yf")
    def test_equity_fallback_to_cache_on_error(
        self, mock_yf: MagicMock, equity_asset: Asset
    ) -> None:
        equity_asset.last_price = Decimal("170.00")
        equity_asset.price_updated_at = None  # stale cache
        equity_asset.save()

        mock_yf.Ticker.side_effect = Exception("Network error")

        price = PricingService.get_current_price(equity_asset)
        assert price == Decimal("170.00")


@pytest.mark.django_db
class TestPortfolioSummary:
    def test_calculate_portfolio_summary(
        self,
        client_obj: Client,
        equity_asset: Asset,
        cash_asset: Asset,
        bond_asset: Asset,
    ) -> None:
        equity_asset.last_price = Decimal("200.00")
        equity_asset.price_updated_at = timezone.now()
        equity_asset.save()

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
        Holding.objects.create(
            client=client_obj,
            asset=bond_asset,
            quantity=Decimal("5"),
            average_cost=Decimal("980.00"),
        )

        with patch("apps.portfolio.services.yf"):
            summary = PricingService.calculate_portfolio_summary(client_obj)

        # equity: 10 * 200 = 2000, cash: 5000, bond: 5 * 1000 = 5000
        assert summary["total_value"] == Decimal("12000")
        assert summary["total_gain_loss"] == Decimal("12000") - (
            Decimal("1500") + Decimal("5000") + Decimal("4900")
        )
        assert len(summary["top_holdings"]) <= 5
        assert "equity_allocation_pct" in summary
        assert "bond_allocation_pct" in summary
        assert "cash_allocation_pct" in summary


@pytest.mark.django_db
class TestCalculatePerformance:
    @patch("apps.portfolio.services.yf")
    def test_calculate_performance_basic(
        self,
        mock_yf: MagicMock,
        client_obj: Client,
        equity_asset: Asset,
    ) -> None:
        mock_ticker = mock_yf.Ticker.return_value
        mock_ticker.fast_info.get.return_value = 200.0

        Holding.objects.create(
            client=client_obj,
            asset=equity_asset,
            quantity=Decimal("10"),
            average_cost=Decimal("150.00"),
        )

        result = PricingService.calculate_performance(client_obj, 30)

        assert result["client_id"] == client_obj.id
        assert result["client_name"] == str(client_obj)
        assert result["period_days"] == 30
        assert result["current_value"] == Decimal("2000.00")
        assert result["cost_basis"] == Decimal("1500.00")
        assert result["total_gain_loss"] == Decimal("500.00")
        assert result["total_return_pct"] == Decimal("33.33")
        assert result["transactions_in_period"] == 0
        assert len(result["holdings_breakdown"]) == 1
        breakdown = result["holdings_breakdown"][0]
        assert breakdown["symbol"] == "AAPL"
        assert breakdown["current_value"] == Decimal("2000.00")
        assert breakdown["cost_basis"] == Decimal("1500.00")

    @patch("apps.portfolio.services.yf")
    def test_calculate_performance_zero_cost_basis(
        self,
        mock_yf: MagicMock,
        client_obj: Client,
        equity_asset: Asset,
    ) -> None:
        mock_ticker = mock_yf.Ticker.return_value
        mock_ticker.fast_info.get.return_value = 100.0

        Holding.objects.create(
            client=client_obj,
            asset=equity_asset,
            quantity=Decimal("5"),
            average_cost=Decimal("0"),
        )

        result = PricingService.calculate_performance(client_obj, 30)
        assert result["total_return_pct"] == Decimal("0")
        breakdown = result["holdings_breakdown"][0]
        assert breakdown["return_pct"] == Decimal("0")
