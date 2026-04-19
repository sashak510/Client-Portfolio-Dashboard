"""Monthly portfolio summary email service."""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any

from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone


def _compute_summary(user: User) -> dict[str, Any]:
    """Compute the monthly summary stats for a user."""
    from django.db.models import Sum

    from apps.portfolio.models import Account, Asset, Dividend, ExchangeRate, Holding, Transaction
    from apps.portfolio.services import PricingService

    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Total portfolio value
    accounts = Account.objects.filter(owner=user).prefetch_related("holdings__asset")
    total_value = Decimal("0")
    all_holdings: list[dict[str, Any]] = []

    for account in accounts:
        for holding in account.holdings.select_related("asset").all():
            price = PricingService.get_current_price(holding.asset)
            current_value = holding.quantity * price
            cost_basis = holding.quantity * holding.average_cost
            currency = getattr(holding.asset, "currency", "GBP") or "GBP"
            fx = ExchangeRate.get_rate(currency, "GBP")
            value_gbp = current_value * fx
            cost_gbp = cost_basis * fx
            total_value += value_gbp

            if holding.asset.asset_type != Asset.AssetType.CASH and cost_gbp > 0:
                return_pct = ((value_gbp - cost_gbp) / cost_gbp * 100).quantize(Decimal("0.01"))
                all_holdings.append({
                    "symbol": holding.asset.symbol,
                    "name": holding.asset.name,
                    "return_pct": return_pct,
                })

    # Best and worst holding by return %
    best_holding = None
    worst_holding = None
    if all_holdings:
        all_holdings.sort(key=lambda h: h["return_pct"], reverse=True)
        best_holding = all_holdings[0]
        worst_holding = all_holdings[-1]

    # Dividends this month
    dividends_this_month = (
        Dividend.objects.filter(
            holding__account__owner=user,
            payment_date__gte=month_start.date(),
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0")
    )

    # Transactions this month
    transactions_this_month = Transaction.objects.filter(
        account__owner=user,
        executed_at__gte=month_start,
    ).count()

    return {
        "total_value": total_value.quantize(Decimal("0.01")),
        "best_holding": best_holding,
        "worst_holding": worst_holding,
        "dividends_this_month": dividends_this_month.quantize(Decimal("0.01")),
        "transactions_this_month": transactions_this_month,
    }


def send_monthly_summary(user: User) -> None:
    """Build and send the monthly portfolio summary email to a user."""
    if not user.email:
        return

    now = datetime.date.today()
    month_label = now.strftime("%B %Y")
    stats = _compute_summary(user)

    context = {
        "username": user.username,
        "month_label": month_label,
        "total_value": stats["total_value"],
        "best_holding": stats["best_holding"],
        "worst_holding": stats["worst_holding"],
        "dividends_this_month": stats["dividends_this_month"],
        "transactions_this_month": stats["transactions_this_month"],
    }

    subject = f"Stasha — Monthly Summary for {month_label}"

    plain_text = (
        f"Hi {user.username},\n\n"
        f"Monthly Portfolio Summary — {month_label}\n"
        f"{'=' * 40}\n"
        f"Total Portfolio Value:        £{stats['total_value']}\n"
        f"Transactions This Month:      {stats['transactions_this_month']}\n"
        f"Dividends Received:           £{stats['dividends_this_month']}\n"
    )
    if stats["best_holding"]:
        plain_text += (
            f"\nBest Performer:  {stats['best_holding']['name']} "
            f"({stats['best_holding']['symbol']})  "
            f"+{stats['best_holding']['return_pct']}%\n"
        )
    if stats["worst_holding"]:
        plain_text += (
            f"Worst Performer: {stats['worst_holding']['name']} "
            f"({stats['worst_holding']['symbol']})  "
            f"{stats['worst_holding']['return_pct']}%\n"
        )
    plain_text += "\n— Stasha\n"

    html_content = render_to_string("accounts/monthly_summary_email.html", context)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=plain_text,
        to=[user.email],
    )
    msg.attach_alternative(html_content, "text/html")
    msg.send()
