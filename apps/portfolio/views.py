"""ViewSets for portfolio models."""

import csv
from datetime import date
from decimal import Decimal

from django.http import HttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.portfolio.filters import AssetFilter, HoldingFilter, TransactionFilter
from apps.portfolio.models import Asset, Client, Holding, Transaction
from apps.portfolio.serializers import (
    AssetSerializer,
    ClientDetailSerializer,
    ClientSerializer,
    HoldingSerializer,
    PerformanceSerializer,
    PortfolioSummarySerializer,
    TransactionSerializer,
)
from apps.portfolio.services import PricingService


class ClientViewSet(viewsets.ModelViewSet):
    """CRUD for clients, scoped to the requesting user."""

    serializer_class = ClientSerializer

    def get_queryset(self):
        return Client.objects.filter(owner=self.request.user)

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ClientDetailSerializer
        return ClientSerializer

    def perform_create(self, serializer) -> None:
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=["get"], url_path="portfolio-summary")
    def portfolio_summary(self, request: Request, pk=None) -> Response:
        """Return portfolio summary analytics for a client."""
        client = self.get_object()
        summary = PricingService.calculate_portfolio_summary(client)
        serializer = PortfolioSummarySerializer(summary)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def transactions(self, request: Request, pk=None) -> Response:
        """Return a filterable transaction list for a client."""
        client = self.get_object()
        queryset = Transaction.objects.filter(client=client).select_related("asset")
        filterset = TransactionFilter(request.query_params, queryset=queryset)
        page = self.paginate_queryset(filterset.qs)
        if page is not None:
            serializer = TransactionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = TransactionSerializer(filterset.qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="export")
    def export(self, request: Request, pk=None) -> HttpResponse:
        """Export holdings or transactions for a client as a CSV file."""
        client = self.get_object()
        export_type = request.query_params.get("type", "")

        if export_type not in ("holdings", "transactions"):
            return Response(
                {"detail": "Invalid export type. Use 'holdings' or 'transactions'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        today = date.today().isoformat()

        if export_type == "holdings":
            filename = f"client_{client.id}_holdings_{today}.csv"
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

            holdings = client.holdings.select_related("asset").all()
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
        filename = f"client_{client.id}_transactions_{today}.csv"
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        writer = csv.writer(response)
        writer.writerow(
            ["Date", "Type", "Asset Symbol", "Asset Name", "Quantity", "Price", "Total Value", "Note"]
        )

        transactions = client.transactions.select_related("asset").order_by("-executed_at")
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
        """Return portfolio performance analytics for a client over a given period."""
        client = self.get_object()

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

        data = PricingService.calculate_performance(client, period_days)
        serializer = PerformanceSerializer(data)
        return Response(serializer.data)


class AssetViewSet(viewsets.ModelViewSet):
    """CRUD for assets."""

    queryset = Asset.objects.all()
    serializer_class = AssetSerializer
    filterset_class = AssetFilter


class HoldingViewSet(viewsets.ModelViewSet):
    """CRUD for holdings, scoped to the requesting user's clients."""

    serializer_class = HoldingSerializer
    filterset_class = HoldingFilter

    def get_queryset(self):
        return Holding.objects.filter(
            client__owner=self.request.user
        ).select_related("asset")


class TransactionViewSet(viewsets.ModelViewSet):
    """CRUD for transactions, scoped to the requesting user's clients."""

    serializer_class = TransactionSerializer
    filterset_class = TransactionFilter

    def get_queryset(self):
        return Transaction.objects.filter(
            client__owner=self.request.user
        ).select_related("asset")
