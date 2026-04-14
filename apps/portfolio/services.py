"""Business logic for pricing and portfolio analytics."""

from decimal import Decimal
from typing import Any

import yfinance as yf
from django.db.models import QuerySet
from django.utils import timezone

from apps.portfolio.models import Asset, Client


class PricingService:
    """Handles asset pricing, caching, and portfolio calculations."""

    CACHE_TTL_MINUTES = 15

    @staticmethod
    def get_current_price(asset: Asset) -> Decimal:
        """Return the current price for an asset.

        - Cash: always Decimal('1.0').
        - Bond: face_value.
        - Equity: fetch from yfinance with caching.
        Falls back to cached price, then Decimal('0').
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

        # Fetch from yfinance
        try:
            ticker = yf.Ticker(asset.symbol)
            price = ticker.fast_info.get("lastPrice")
            if price is None:
                price = (ticker.info or {}).get("currentPrice")
            if price is not None:
                asset.last_price = Decimal(str(price))
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
    def calculate_portfolio_summary(client: Client) -> dict[str, Any]:
        """Return a full portfolio summary dict for a client."""
        holdings = client.holdings.select_related("asset").all()

        total_value = Decimal("0")
        total_cost = Decimal("0")
        equity_value = Decimal("0")
        bond_value = Decimal("0")
        cash_value = Decimal("0")
        holding_values: list[dict[str, Any]] = []

        for holding in holdings:
            price = PricingService.get_current_price(holding.asset)
            current_value = holding.quantity * price
            cost_basis = holding.quantity * holding.average_cost
            total_value += current_value
            total_cost += cost_basis

            if holding.asset.asset_type == Asset.AssetType.EQUITY:
                equity_value += current_value
            elif holding.asset.asset_type == Asset.AssetType.BOND:
                bond_value += current_value
            elif holding.asset.asset_type == Asset.AssetType.CASH:
                cash_value += current_value

            holding_values.append(
                {
                    "symbol": holding.asset.symbol,
                    "name": holding.asset.name,
                    "asset_type": holding.asset.asset_type,
                    "quantity": holding.quantity,
                    "current_value": current_value,
                    "gain_loss": current_value - cost_basis,
                }
            )

        # Sort by value descending, take top 5
        holding_values.sort(key=lambda h: h["current_value"], reverse=True)
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
        }

    @staticmethod
    def calculate_performance(client: Client, period_days: int) -> dict[str, Any]:
        """Calculate portfolio performance over the given period (7/30/90/365 days)."""
        from datetime import timedelta

        from django.db.models import Sum
        from django.utils import timezone

        from apps.portfolio.models import Transaction

        now = timezone.now()
        end_date = now.date()
        start_date = (now - timedelta(days=period_days)).date()

        holdings = client.holdings.select_related("asset").all()

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
            client=client,
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
            "client_id": client.id,
            "client_name": str(client),
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
