"""Business logic for pricing and portfolio analytics."""

from decimal import Decimal
from typing import Any

import requests
import yfinance as yf
from django.conf import settings
from django.db.models import QuerySet
from django.utils import timezone

from apps.portfolio.models import Account, Asset, Dividend, ExchangeRate

_ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"


class PricingService:
    """Handles asset pricing, caching, and portfolio calculations."""

    CACHE_TTL_MINUTES = 15

    @staticmethod
    def get_current_price(asset: Asset) -> Decimal:
        """Return the current price for an asset.

        - Cash: always Decimal('1.0').
        - Bond: face_value.
        - Equity: fetch from Alpha Vantage GLOBAL_QUOTE with 15-min caching.
        Falls back to asset.last_price, then Decimal('0') if unavailable.
        """
        if asset.asset_type == Asset.AssetType.CASH:
            return Decimal("1.0")

        if asset.asset_type == Asset.AssetType.BOND:
            return asset.face_value if asset.face_value else Decimal("0")

        # Equity — check cache freshness
        now = timezone.now()
        if (
            asset.last_price is not None
            and asset.price_updated_at is not None
            and (now - asset.price_updated_at).total_seconds()
            < PricingService.CACHE_TTL_MINUTES * 60
        ):
            return asset.last_price

        # Fetch live price via yfinance
        try:
            ticker = yf.Ticker(asset.symbol)
            raw = ticker.fast_info.get("lastPrice") or ticker.fast_info.get("regularMarketPrice")
            if raw is not None:
                asset.last_price = Decimal(str(raw))
                asset.price_updated_at = now
                asset.save(update_fields=["last_price", "price_updated_at"])
                return asset.last_price
        except Exception:
            pass

        # Fallback to cached price
        if asset.last_price is not None:
            return asset.last_price
        return Decimal("0")

    @staticmethod
    def refresh_prices(assets: QuerySet) -> dict[str, Decimal]:
        """Bulk-refresh prices for a queryset of assets."""
        results: dict[str, Decimal] = {}
        for asset in assets:
            results[asset.symbol] = PricingService.get_current_price(asset)
        return results

    @staticmethod
    def calculate_portfolio_summary(account: Account) -> dict[str, Any]:
        """Return a full portfolio summary dict for an account."""
        from django.db.models import Sum

        holdings = account.holdings.select_related("asset").all()

        total_value = Decimal("0")
        total_cost = Decimal("0")
        equity_value = Decimal("0")
        bond_value = Decimal("0")
        cash_value = Decimal("0")
        total_dividends = Decimal("0")
        holding_values: list[dict[str, Any]] = []

        for holding in holdings:
            price = PricingService.get_current_price(holding.asset)
            current_value = holding.quantity * price
            cost_basis = holding.quantity * holding.average_cost

            # Convert to GBP using exchange rate
            currency = getattr(holding.asset, "currency", "GBP") or "GBP"
            fx_rate = ExchangeRate.get_rate(currency, "GBP")
            value_in_gbp = current_value * fx_rate
            cost_in_gbp = cost_basis * fx_rate

            total_value += value_in_gbp
            total_cost += cost_in_gbp

            if holding.asset.asset_type == Asset.AssetType.EQUITY:
                equity_value += value_in_gbp
            elif holding.asset.asset_type == Asset.AssetType.BOND:
                bond_value += value_in_gbp
            elif holding.asset.asset_type == Asset.AssetType.CASH:
                cash_value += value_in_gbp

            # Dividend totals per holding
            holding_dividends = (
                Dividend.objects.filter(holding=holding).aggregate(
                    total=Sum("amount")
                )["total"]
                or Decimal("0")
            )
            total_dividends += holding_dividends
            dividend_yield_pct = (
                (holding_dividends / value_in_gbp * 100).quantize(Decimal("0.01"))
                if value_in_gbp > 0
                else Decimal("0")
            )

            holding_values.append(
                {
                    "symbol": holding.asset.symbol,
                    "name": holding.asset.name,
                    "asset_type": holding.asset.asset_type,
                    "currency": currency,
                    "quantity": holding.quantity,
                    "current_value": current_value,
                    "value_in_gbp": value_in_gbp,
                    "gain_loss": value_in_gbp - cost_in_gbp,
                    "total_dividends": holding_dividends,
                    "dividend_yield_percent": dividend_yield_pct,
                }
            )

        # Sort by GBP value descending, take top 5
        holding_values.sort(key=lambda h: h["value_in_gbp"], reverse=True)
        top_holdings = holding_values[:5]

        if total_value > 0:
            equity_pct = (equity_value / total_value * 100).quantize(Decimal("0.01"))
            bond_pct = (bond_value / total_value * 100).quantize(Decimal("0.01"))
            cash_pct = (cash_value / total_value * 100).quantize(Decimal("0.01"))
        else:
            equity_pct = bond_pct = cash_pct = Decimal("0")

        return {
            "total_value": total_value,
            "total_gain_loss": total_value - total_cost,
            "equity_allocation_pct": equity_pct,
            "bond_allocation_pct": bond_pct,
            "cash_allocation_pct": cash_pct,
            "top_holdings": top_holdings,
            "total_dividends": total_dividends,
        }

    @staticmethod
    def calculate_performance(account: Account, period_days: int) -> dict[str, Any]:
        """Calculate portfolio performance over the given period (7/30/90/365 days)."""
        from datetime import timedelta

        from django.db.models import Sum
        from django.utils import timezone

        from apps.portfolio.models import Transaction

        now = timezone.now()
        end_date = now.date()
        start_date = (now - timedelta(days=period_days)).date()

        holdings = account.holdings.select_related("asset").all()

        total_current_value = Decimal("0")
        total_cost_basis = Decimal("0")
        holdings_breakdown: list[dict[str, Any]] = []

        for holding in holdings:
            price = PricingService.get_current_price(holding.asset)
            current_value = holding.quantity * price
            cost_basis = holding.quantity * holding.average_cost
            gain_loss = current_value - cost_basis
            return_pct = (
                ((current_value - cost_basis) / cost_basis * 100).quantize(Decimal("0.01"))
                if cost_basis != 0
                else Decimal("0")
            )
            total_current_value += current_value
            total_cost_basis += cost_basis
            holdings_breakdown.append(
                {
                    "symbol": holding.asset.symbol,
                    "name": holding.asset.name,
                    "asset_type": holding.asset.asset_type,
                    "quantity": holding.quantity,
                    "cost_basis": cost_basis.quantize(Decimal("0.01")),
                    "current_value": current_value.quantize(Decimal("0.01")),
                    "gain_loss": gain_loss.quantize(Decimal("0.01")),
                    "return_pct": return_pct,
                }
            )

        holdings_breakdown.sort(key=lambda h: h["current_value"], reverse=True)

        total_gain_loss = total_current_value - total_cost_basis
        total_return_pct = (
            ((total_gain_loss / total_cost_basis) * 100).quantize(Decimal("0.01"))
            if total_cost_basis != 0
            else Decimal("0")
        )

        period_txns = Transaction.objects.filter(
            account=account,
            executed_at__date__gte=start_date,
            executed_at__date__lte=end_date,
        )
        transactions_in_period = period_txns.count()

        inflow = (
            period_txns.filter(
                transaction_type__in=[
                    Transaction.TransactionType.BUY,
                    Transaction.TransactionType.DEPOSIT,
                ]
            ).aggregate(total=Sum("total_value"))["total"]
            or Decimal("0")
        )
        outflow = (
            period_txns.filter(
                transaction_type__in=[
                    Transaction.TransactionType.SELL,
                    Transaction.TransactionType.WITHDRAW,
                ]
            ).aggregate(total=Sum("total_value"))["total"]
            or Decimal("0")
        )
        net_invested_in_period = inflow - outflow

        return {
            "account_id": account.id,
            "account_name": str(account),
            "period_days": period_days,
            "start_date": start_date,
            "end_date": end_date,
            "current_value": total_current_value.quantize(Decimal("0.01")),
            "cost_basis": total_cost_basis.quantize(Decimal("0.01")),
            "total_gain_loss": total_gain_loss.quantize(Decimal("0.01")),
            "total_return_pct": total_return_pct,
            "transactions_in_period": transactions_in_period,
            "net_invested_in_period": net_invested_in_period.quantize(Decimal("0.01")),
            "holdings_breakdown": holdings_breakdown,
        }
