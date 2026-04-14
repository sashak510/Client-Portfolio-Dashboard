"""ViewSets for portfolio models."""

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
