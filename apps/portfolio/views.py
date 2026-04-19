"""ViewSets for portfolio models."""

import csv
import io
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.http import HttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.mixins import AuditLogMixin
from apps.portfolio.filters import AssetFilter, HoldingFilter, TransactionFilter
from apps.portfolio.models import (
    Account,
    Asset,
    Dividend,
    ExchangeRate,
    Goal,
    Holding,
    Liability,
    NonInvestmentAccount,
    PortfolioSnapshot,
    RecurringContribution,
    TargetAllocation,
    Transaction,
    WatchlistItem,
)
from apps.portfolio.serializers import (
    AccountDetailSerializer,
    AccountSerializer,
    AssetSerializer,
    DividendSerializer,
    GoalSerializer,
    HoldingSerializer,
    LiabilitySerializer,
    NonInvestmentAccountSerializer,
    PerformanceSerializer,
    PortfolioSnapshotSerializer,
    PortfolioSummarySerializer,
    RecurringContributionSerializer,
    TargetAllocationSerializer,
    TransactionSerializer,
    WatchlistItemSerializer,
)
from apps.portfolio.services import PricingService


class AccountViewSet(AuditLogMixin, viewsets.ModelViewSet):
    """CRUD for your accounts."""

    serializer_class = AccountSerializer

    def get_queryset(self):
        return Account.objects.filter(owner=self.request.user)

    def get_serializer_class(self):
        if self.action == "retrieve":
            return AccountDetailSerializer
        return AccountSerializer

    def perform_create(self, serializer) -> None:
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=["get"], url_path="portfolio-summary")
    def portfolio_summary(self, request: Request, pk=None) -> Response:
        """Return portfolio summary analytics for an account."""
        account = self.get_object()
        summary = PricingService.calculate_portfolio_summary(account)
        serializer = PortfolioSummarySerializer(summary)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def transactions(self, request: Request, pk=None) -> Response:
        """Return a filterable transaction list for an account."""
        account = self.get_object()
        queryset = Transaction.objects.filter(account=account).select_related("asset")
        filterset = TransactionFilter(request.query_params, queryset=queryset)
        page = self.paginate_queryset(filterset.qs)
        if page is not None:
            serializer = TransactionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = TransactionSerializer(filterset.qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="export")
    def export(self, request: Request, pk=None) -> HttpResponse:
        """Export holdings or transactions for an account as a CSV file."""
        account = self.get_object()
        export_type = request.query_params.get("type", "")

        if export_type not in ("holdings", "transactions"):
            return Response(
                {"detail": "Invalid export type. Use 'holdings' or 'transactions'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        today = date.today().isoformat()

        if export_type == "holdings":
            filename = f"account_{account.id}_holdings_{today}.csv"
            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = f'attachment; filename="{filename}"'

            writer = csv.writer(response)
            writer.writerow(
                [
                    "Asset Symbol",
                    "Asset Name",
                    "Asset Type",
                    "Quantity",
                    "Average Cost",
                    "Current Value",
                    "Gain/Loss",
                    "Allocation %",
                ]
            )

            holdings = account.holdings.select_related("asset").all()
            holding_rows = []
            total_portfolio_value = Decimal("0")

            for holding in holdings:
                price = PricingService.get_current_price(holding.asset)
                current_value = holding.quantity * price
                total_portfolio_value += current_value
                holding_rows.append((holding, current_value))

            for holding, current_value in holding_rows:
                cost_basis = holding.quantity * holding.average_cost
                gain_loss = current_value - cost_basis
                allocation_pct = (
                    round(float(current_value / total_portfolio_value * 100), 2)
                    if total_portfolio_value
                    else 0.0
                )
                writer.writerow(
                    [
                        holding.asset.symbol,
                        holding.asset.name,
                        holding.asset.get_asset_type_display(),
                        holding.quantity,
                        holding.average_cost,
                        round(float(current_value), 2),
                        round(float(gain_loss), 2),
                        allocation_pct,
                    ]
                )

            return response

        # export_type == "transactions"
        filename = f"account_{account.id}_transactions_{today}.csv"
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow(
            ["Date", "Type", "Asset Symbol", "Asset Name", "Quantity", "Price", "Total Value", "Note"]
        )

        transactions = account.transactions.select_related("asset").order_by("-executed_at")
        for txn in transactions:
            writer.writerow(
                [
                    txn.executed_at.date().isoformat(),
                    txn.get_transaction_type_display(),
                    txn.asset.symbol,
                    txn.asset.name,
                    txn.quantity,
                    txn.price,
                    txn.total_value,
                    txn.note,
                ]
            )

        return response

    @action(detail=True, methods=["get"], url_path="performance")
    def performance(self, request: Request, pk=None) -> Response:
        """Return portfolio performance analytics for an account over a given period."""
        account = self.get_object()

        VALID_PERIODS = {7, 30, 90, 365}
        try:
            period_days = int(request.query_params.get("period", 30))
        except (TypeError, ValueError):
            period_days = -1

        if period_days not in VALID_PERIODS:
            return Response(
                {"detail": "Invalid period. Use 7, 30, 90, or 365."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = PricingService.calculate_performance(account, period_days)
        serializer = PerformanceSerializer(data)
        return Response(serializer.data)


class AssetViewSet(viewsets.ModelViewSet):
    """CRUD for assets."""

    queryset = Asset.objects.all()
    serializer_class = AssetSerializer
    filterset_class = AssetFilter


class HoldingViewSet(AuditLogMixin, viewsets.ModelViewSet):
    """CRUD for holdings, scoped to your accounts."""

    serializer_class = HoldingSerializer
    filterset_class = HoldingFilter

    def get_queryset(self):
        return Holding.objects.filter(
            account__owner=self.request.user
        ).select_related("asset")


class TransactionViewSet(AuditLogMixin, viewsets.ModelViewSet):
    """CRUD for transactions, scoped to your accounts."""

    serializer_class = TransactionSerializer
    filterset_class = TransactionFilter

    def get_queryset(self):
        return Transaction.objects.filter(
            account__owner=self.request.user
        ).select_related("asset")


class TargetAllocationViewSet(viewsets.ModelViewSet):
    """CRUD for target allocations, scoped to your accounts."""

    serializer_class = TargetAllocationSerializer
    filterset_fields = ("account", "asset_type")

    def get_queryset(self):
        return TargetAllocation.objects.filter(
            account__owner=self.request.user
        ).select_related("account")


class DividendViewSet(viewsets.ModelViewSet):
    """CRUD for dividends, scoped to your accounts."""

    serializer_class = DividendSerializer
    filterset_fields = ("holding",)

    def get_queryset(self):
        return Dividend.objects.filter(
            holding__account__owner=self.request.user
        ).select_related("holding__asset", "holding__account")


class WatchlistItemViewSet(viewsets.ModelViewSet):
    """CRUD for watchlist items, scoped to the authenticated user."""

    serializer_class = WatchlistItemSerializer

    def get_queryset(self):
        return WatchlistItem.objects.filter(
            user=self.request.user
        ).select_related("asset")

    def perform_create(self, serializer) -> None:
        serializer.save(user=self.request.user)


class NonInvestmentAccountViewSet(viewsets.ModelViewSet):
    """CRUD for non-investment accounts, scoped to the authenticated user."""

    serializer_class = NonInvestmentAccountSerializer

    def get_queryset(self):
        return NonInvestmentAccount.objects.filter(user=self.request.user)

    def perform_create(self, serializer) -> None:
        serializer.save(user=self.request.user)


class LiabilityViewSet(viewsets.ModelViewSet):
    """CRUD for liabilities, scoped to the authenticated user."""

    serializer_class = LiabilitySerializer

    def get_queryset(self):
        return Liability.objects.filter(user=self.request.user)

    def perform_create(self, serializer) -> None:
        serializer.save(user=self.request.user)


class NetWorthSummaryView(APIView):
    """Return a net worth summary: investment total + non-investment total."""

    def get(self, request: Request) -> Response:
        user = request.user

        investment_total = Decimal("0")
        investment_by_type: dict = {"equity": Decimal("0"), "bond": Decimal("0"), "cash": Decimal("0")}
        breakdown = []
        for account in Account.objects.filter(owner=user).prefetch_related("holdings__asset"):
            account_value = Decimal("0")
            for holding in account.holdings.select_related("asset").all():
                price = holding.asset.last_price if holding.asset.last_price else Decimal("0")
                if holding.asset.asset_type == "cash":
                    price = Decimal("1.0")
                elif holding.asset.asset_type == "bond":
                    price = holding.asset.face_value if holding.asset.face_value else Decimal("0")
                value = holding.quantity * price
                fx_rate = ExchangeRate.get_rate(getattr(holding.asset, "currency", "GBP") or "GBP")
                converted = value * fx_rate
                account_value += converted
                if holding.asset.asset_type in investment_by_type:
                    investment_by_type[holding.asset.asset_type] += converted
            investment_total += account_value
            breakdown.append({
                "name": account.account_name,
                "type": account.account_type,
                "balance": str(round(account_value, 2)),
                "category": "investment",
            })

        non_investment_total = Decimal("0")
        for nia in NonInvestmentAccount.objects.filter(user=user):
            non_investment_total += nia.balance
            breakdown.append({
                "name": nia.name,
                "type": nia.account_type,
                "balance": str(nia.balance),
                "category": "non_investment",
            })

        liabilities_total = Decimal("0")
        for liability in Liability.objects.filter(user=user):
            liabilities_total += liability.balance
            breakdown.append({
                "name": liability.name,
                "type": liability.liability_type,
                "balance": str(liability.balance),
                "category": "liability",
            })

        return Response({
            "investment_total": str(round(investment_total, 2)),
            "non_investment_total": str(round(non_investment_total, 2)),
            "liabilities_total": str(round(liabilities_total, 2)),
            "total_net_worth": str(round(investment_total + non_investment_total - liabilities_total, 2)),
            "investment_by_asset_type": {k: str(round(v, 2)) for k, v in investment_by_type.items()},
            "breakdown": breakdown,
        })


class RecurringContributionViewSet(viewsets.ModelViewSet):
    """CRUD for recurring contributions, scoped to the authenticated user."""

    serializer_class = RecurringContributionSerializer

    def get_queryset(self):
        return RecurringContribution.objects.filter(user=self.request.user).select_related("account")

    def perform_create(self, serializer) -> None:
        serializer.save(user=self.request.user)


class ContributionHistoryView(APIView):
    """Return monthly BUY transaction totals grouped by month."""

    def get(self, request: Request) -> Response:
        user = request.user
        account_id = request.query_params.get("account")

        txns = Transaction.objects.filter(
            account__owner=user,
            transaction_type=Transaction.TransactionType.BUY,
        ).select_related("account")

        if account_id:
            txns = txns.filter(account_id=account_id)

        monthly: dict = defaultdict(Decimal)
        for txn in txns.order_by("executed_at"):
            key = txn.executed_at.strftime("%Y-%m")
            monthly[key] += txn.total_value

        result = [
            {"month": k, "total_contributed": str(round(v, 2))}
            for k, v in sorted(monthly.items())
        ]
        return Response(result)


class GoalViewSet(viewsets.ModelViewSet):
    """CRUD for goals, scoped to the authenticated user."""

    serializer_class = GoalSerializer

    def get_queryset(self):
        return Goal.objects.filter(user=self.request.user).select_related("account")

    def perform_create(self, serializer) -> None:
        serializer.save(user=self.request.user)


# ── Broker CSV mappers ────────────────────────────────────────────────────────
#
# Each mapper receives a dict of raw (lowercased, stripped) CSV columns and an
# account_id string supplied by the upload form.  Return a dict with canonical
# keys: symbol, quantity, price, date (YYYY-MM-DD), type (buy|sell), account_id.
# Raise ValueError with a human-readable message to skip a row.

def _map_trading212(raw: dict, account_id: str) -> dict:
    """Map a Trading 212 activity CSV row to the canonical schema.

    Verified columns (Trading 212 export as of 2024):
      Action, Time, ISIN, Ticker, Name, No. of shares, Price / share,
      Currency (Price / share), Exchange rate, Result, Currency (Result),
      Total, Currency (Total), Withholding tax, Currency (Withholding tax),
      Charge amount (EUR), Currency (Charge amount (EUR)), Transaction ID, Notes
    """
    action = raw.get("action", "").lower()
    if "buy" in action:
        tx_type = "buy"
    elif "sell" in action:
        tx_type = "sell"
    else:
        raise ValueError(f"unrecognised Action '{raw.get('action', '')}' (expected buy/sell)")

    ticker = raw.get("ticker", "").strip().upper()
    if not ticker:
        raise ValueError("Ticker is empty")

    shares_str = raw.get("no. of shares", "").replace(",", "")
    price_str = raw.get("price / share", "").replace(",", "")

    # Time format exported by T212: "2024-01-15 09:30:00"
    time_str = raw.get("time", "")
    date_str = time_str[:10]  # YYYY-MM-DD prefix

    return {
        "symbol": ticker,
        "quantity": shares_str,
        "price": price_str,
        "date": date_str,
        "type": tx_type,
        "account_id": account_id,
    }


# TODO: verify real Vanguard UK export column names before implementing
def _map_vanguard_uk(raw: dict, account_id: str) -> dict:
    raise ValueError(
        "Vanguard UK preset is coming soon — export as Generic CSV in the meantime"
    )


# TODO: verify real AJ Bell export column names before implementing
def _map_aj_bell(raw: dict, account_id: str) -> dict:
    raise ValueError(
        "AJ Bell preset is coming soon — export as Generic CSV in the meantime"
    )


_BROKER_MAPPERS: dict = {
    "trading212": _map_trading212,
    "vanguard_uk": _map_vanguard_uk,
    "aj_bell": _map_aj_bell,
}

_BROKER_SAMPLES: dict = {
    "generic": (
        "symbol,quantity,price,date,type,account_id\n"
        "AAPL,10,178.50,2024-01-15,buy,1\n"
        "MSFT,5,415.20,2024-02-10,buy,1\n"
    ),
    "trading212": (
        "Action,Time,ISIN,Ticker,Name,No. of shares,Price / share,"
        "Currency (Price / share),Exchange rate,Result,Currency (Result),"
        "Total,Currency (Total),Withholding tax,Currency (Withholding tax),"
        "Charge amount (EUR),Currency (Charge amount (EUR)),Transaction ID,Notes\n"
        "Market buy,2024-01-15 09:30:00,US0378331005,AAPL,Apple Inc.,10,178.50,"
        "USD,1.00,,,1785.00,USD,,,,,,TX001,\n"
        "Market sell,2024-02-10 14:45:00,US5949181045,MSFT,Microsoft Corp.,5,415.20,"
        "USD,1.00,76.00,USD,2076.00,USD,,,,,,TX002,\n"
    ),
    "vanguard_uk": "# Vanguard UK preset coming soon\n",
    "aj_bell": "# AJ Bell preset coming soon\n",
}


class CSVSampleView(APIView):
    """Serve a sample CSV download for a given broker preset."""

    def get(self, request: Request, broker: str) -> HttpResponse:
        broker = broker.lower()
        content = _BROKER_SAMPLES.get(broker)
        if content is None:
            return Response(
                {"detail": f"Unknown broker '{broker}'."},
                status=status.HTTP_404_NOT_FOUND,
            )
        response = HttpResponse(content, content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="sample_{broker}.csv"'
        return response


class CSVImportView(APIView):
    """Import transactions from a CSV file upload."""

    parser_classes = (MultiPartParser, FormParser)

    def post(self, request: Request) -> Response:
        csv_file = request.FILES.get("file")
        if not csv_file:
            return Response(
                {"detail": "No file uploaded. Send a CSV file as 'file'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        broker = request.data.get("broker", "generic").lower()
        broker_mapper = _BROKER_MAPPERS.get(broker)  # None → generic path
        account_id_form = request.data.get("account_id", "")

        # Attempt to decode the CSV
        try:
            decoded = csv_file.read().decode("utf-8")
        except UnicodeDecodeError:
            return Response(
                {"detail": "File is not valid UTF-8."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reader = csv.DictReader(io.StringIO(decoded))

        if reader.fieldnames is None:
            return Response(
                {"imported": 0, "skipped": 0, "errors": ["Empty CSV file or no header row."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Generic path only: validate required columns up-front.
        # Broker mappers validate per-row via their own logic.
        if broker_mapper is None:
            required_columns = {"symbol", "quantity", "price", "date", "type", "account_id"}
            actual_columns = {c.strip().lower() for c in reader.fieldnames}
            missing = required_columns - actual_columns
            if missing:
                return Response(
                    {
                        "imported": 0,
                        "skipped": 0,
                        "errors": [f"Missing required columns: {', '.join(sorted(missing))}"],
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        imported = 0
        skipped = 0
        errors = []

        for row_num, row in enumerate(reader, start=2):  # row 2 because row 1 is header
            raw = {k.strip().lower(): v.strip() for k, v in row.items() if k}

            if broker_mapper is not None:
                try:
                    mapped = broker_mapper(raw, account_id_form)
                except ValueError as exc:
                    errors.append(f"row {row_num}: {exc}")
                    skipped += 1
                    continue
                symbol = mapped.get("symbol", "").upper()
                quantity_str = mapped.get("quantity", "")
                price_str = mapped.get("price", "")
                date_str = mapped.get("date", "")
                tx_type = mapped.get("type", "").lower()
                account_id_str = mapped.get("account_id", "")
            else:
                symbol = raw.get("symbol", "").upper()
                quantity_str = raw.get("quantity", "")
                price_str = raw.get("price", "")
                date_str = raw.get("date", "")
                tx_type = raw.get("type", "").lower()
                account_id_str = raw.get("account_id", "")

            # Validate required fields are non-empty
            if not all([symbol, quantity_str, price_str, date_str, tx_type, account_id_str]):
                errors.append(f"row {row_num}: missing required field(s)")
                skipped += 1
                continue

            # Validate transaction type
            if tx_type not in ("buy", "sell"):
                errors.append(f"row {row_num}: invalid type '{tx_type}' (must be buy or sell)")
                skipped += 1
                continue

            # Validate numeric fields
            try:
                quantity = Decimal(quantity_str)
                price = Decimal(price_str)
            except (InvalidOperation, ValueError):
                errors.append(f"row {row_num}: invalid quantity or price")
                skipped += 1
                continue

            if quantity <= 0 or price <= 0:
                errors.append(f"row {row_num}: quantity and price must be positive")
                skipped += 1
                continue

            # Validate date
            try:
                executed_date = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                errors.append(f"row {row_num}: invalid date '{date_str}' (expected YYYY-MM-DD)")
                skipped += 1
                continue

            # Validate account_id
            try:
                account_id = int(account_id_str)
            except ValueError:
                errors.append(f"row {row_num}: invalid account_id '{account_id_str}'")
                skipped += 1
                continue

            # Verify account belongs to the user
            try:
                account = Account.objects.get(id=account_id, owner=request.user)
            except Account.DoesNotExist:
                errors.append(f"row {row_num}: account {account_id} not found or not owned by you")
                skipped += 1
                continue

            # Look up or create Asset
            asset, _created = Asset.objects.get_or_create(
                symbol=symbol,
                defaults={
                    "name": symbol,
                    "asset_type": Asset.AssetType.EQUITY,
                },
            )

            total_value = quantity * price

            # Create Transaction
            from django.utils import timezone as tz

            Transaction.objects.create(
                account=account,
                asset=asset,
                transaction_type=tx_type,
                quantity=quantity,
                price=price,
                total_value=total_value,
                executed_at=tz.make_aware(executed_date) if tz.is_naive(executed_date) else executed_date,
            )

            # Update or create Holding
            try:
                holding = Holding.objects.get(account=account, asset=asset)
                if tx_type == "buy":
                    new_total_cost = (holding.quantity * holding.average_cost) + (quantity * price)
                    holding.quantity += quantity
                    if holding.quantity > 0:
                        holding.average_cost = new_total_cost / holding.quantity
                elif tx_type == "sell":
                    holding.quantity -= quantity
                    # average_cost stays the same on sell
                holding.save()
            except Holding.DoesNotExist:
                if tx_type == "buy":
                    Holding.objects.create(
                        account=account,
                        asset=asset,
                        quantity=quantity,
                        average_cost=price,
                    )
                else:
                    errors.append(f"row {row_num}: cannot sell {symbol} — no existing holding")
                    skipped += 1
                    continue

            imported += 1

        return Response(
            {"imported": imported, "skipped": skipped, "errors": errors},
            status=status.HTTP_200_OK,
        )


# ── Snapshots ─────────────────────────────────────────────────────────────────

def _build_snapshot_for_user(user):
    """Compute and upsert today's PortfolioSnapshot for the given user."""
    from django.utils import timezone as _tz

    today = _tz.now().date()
    accounts = Account.objects.filter(owner=user).prefetch_related("holdings__asset")

    total_value = Decimal("0")
    account_snapshots = []

    for account in accounts:
        acc_value = Decimal("0")
        for holding in account.holdings.select_related("asset").all():
            price = PricingService.get_current_price(holding.asset)
            curr = holding.quantity * price
            currency = getattr(holding.asset, "currency", "GBP") or "GBP"
            fx = ExchangeRate.get_rate(currency, "GBP")
            acc_value += curr * fx
        total_value += acc_value
        account_snapshots.append({
            "account_id": account.id,
            "account_name": account.account_name,
            "value": str(acc_value.quantize(Decimal("0.01"))),
        })

    snapshot, _ = PortfolioSnapshot.objects.update_or_create(
        user=user,
        date=today,
        defaults={
            "total_value": total_value.quantize(Decimal("0.01")),
            "account_snapshots": account_snapshots,
        },
    )
    return snapshot


class SnapshotViewSet(viewsets.ReadOnlyModelViewSet):
    """List and retrieve portfolio snapshots for the authenticated user."""

    serializer_class = PortfolioSnapshotSerializer

    def get_queryset(self):
        qs = PortfolioSnapshot.objects.filter(user=self.request.user)
        if not qs.exists() and Account.objects.filter(owner=self.request.user).exists():
            _build_snapshot_for_user(self.request.user)
            qs = PortfolioSnapshot.objects.filter(user=self.request.user)
        return qs.order_by("-date")


class TakeSnapshotView(APIView):
    """Trigger an immediate snapshot for the current user — POST /api/snapshots/take/."""

    def post(self, request: Request) -> Response:
        snapshot = _build_snapshot_for_user(request.user)
        serializer = PortfolioSnapshotSerializer(snapshot)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ExportDataView(APIView):
    """Export all user data as a multi-sheet CSV zip — GET /api/export/."""

    def get(self, request: Request) -> HttpResponse:
        import zipfile
        import io as _io

        user = request.user
        buf = _io.BytesIO()

        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            # Accounts
            acc_buf = io.StringIO()
            w = csv.writer(acc_buf)
            w.writerow(["id", "name", "type", "provider", "created_at"])
            for a in Account.objects.filter(owner=user):
                w.writerow([a.id, a.account_name, a.account_type, a.provider, a.created_at.date()])
            zf.writestr("accounts.csv", acc_buf.getvalue())

            # Holdings
            h_buf = io.StringIO()
            w = csv.writer(h_buf)
            w.writerow(["id", "account", "symbol", "asset_name", "quantity", "avg_buy_price", "notes"])
            for h in Holding.objects.filter(account__owner=user).select_related("account", "asset"):
                w.writerow([h.id, h.account.account_name, h.asset.symbol, h.asset.name, h.quantity, h.avg_buy_price, h.notes])
            zf.writestr("holdings.csv", h_buf.getvalue())

            # Transactions
            t_buf = io.StringIO()
            w = csv.writer(t_buf)
            w.writerow(["id", "account", "symbol", "type", "quantity", "price", "date"])
            for t in Transaction.objects.filter(account__owner=user).select_related("account", "asset"):
                w.writerow([t.id, t.account.account_name, t.asset.symbol, t.transaction_type, t.quantity, t.price, t.date])
            zf.writestr("transactions.csv", t_buf.getvalue())

            # Watchlist
            wl_buf = io.StringIO()
            w = csv.writer(wl_buf)
            w.writerow(["symbol", "name", "target_price", "notes"])
            for item in WatchlistItem.objects.filter(owner=user).select_related("asset"):
                w.writerow([item.asset.symbol, item.asset.name, item.target_price or "", item.notes])
            zf.writestr("watchlist.csv", wl_buf.getvalue())

        buf.seek(0)
        response = HttpResponse(buf.read(), content_type="application/zip")
        response["Content-Disposition"] = 'attachment; filename="stash-export.zip"'
        return response
