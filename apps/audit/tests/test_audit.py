"""Tests for the audit logging app."""

from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient

from apps.audit.models import AuditLog
from apps.portfolio.models import Account, Asset, Holding


@pytest.fixture
def admin_user(db) -> User:
    return User.objects.create_superuser(
        username="admin", password="adminpass", email="admin@example.com"
    )


@pytest.fixture
def regular_user(db) -> User:
    return User.objects.create_user(username="user1", password="pass123")


@pytest.fixture
def admin_client(admin_user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def user_client(regular_user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=regular_user)
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
def account_obj(regular_user: User) -> Account:
    return Account.objects.create(
        owner=regular_user,
        account_name="Vanguard ISA",
        account_type=Account.AccountType.ISA,
        provider="Vanguard",
    )


@pytest.mark.django_db
class TestAuditOnCreate:
    def test_create_account_generates_audit_log(self, user_client: APIClient) -> None:
        data = {
            "account_name": "AJ Bell SIPP",
            "account_type": "sipp",
            "provider": "AJ Bell",
        }
        response = user_client.post("/api/accounts/", data)
        assert response.status_code == 201

        assert AuditLog.objects.count() == 1
        log = AuditLog.objects.first()
        assert log.action == "create"
        assert log.model_name == "Account"

    def test_audit_log_captures_user(
        self, user_client: APIClient, regular_user: User
    ) -> None:
        data = {
            "account_name": "Test GIA",
            "account_type": "gia",
        }
        user_client.post("/api/accounts/", data)

        log = AuditLog.objects.first()
        assert log.user == regular_user

    def test_audit_log_captures_ip(self, user_client: APIClient) -> None:
        data = {
            "account_name": "Test Savings",
            "account_type": "savings",
        }
        user_client.post("/api/accounts/", data)

        log = AuditLog.objects.first()
        assert log.ip_address is not None


@pytest.mark.django_db
class TestAuditOnUpdate:
    def test_update_account_generates_audit_log_with_changes(
        self, user_client: APIClient, account_obj: Account
    ) -> None:
        response = user_client.patch(
            f"/api/accounts/{account_obj.id}/",
            {"account_name": "Vanguard ISA (Updated)"},
        )
        assert response.status_code == 200

        log = AuditLog.objects.filter(action="update").first()
        assert log is not None
        assert log.model_name == "Account"
        assert "account_name" in log.changes
        assert log.changes["account_name"]["old"] == "Vanguard ISA"
        assert log.changes["account_name"]["new"] == "Vanguard ISA (Updated)"


@pytest.mark.django_db
class TestAuditOnDelete:
    def test_delete_holding_generates_audit_log(
        self, user_client: APIClient, account_obj: Account, equity_asset: Asset
    ) -> None:
        holding = Holding.objects.create(
            account=account_obj,
            asset=equity_asset,
            quantity=Decimal("10"),
            average_cost=Decimal("150.00"),
        )
        response = user_client.delete(f"/api/holdings/{holding.id}/")
        assert response.status_code == 204

        log = AuditLog.objects.filter(action="delete").first()
        assert log is not None
        assert log.model_name == "Holding"


@pytest.mark.django_db
class TestAuditAPIAccess:
    def test_audit_api_admin_only(self, user_client: APIClient) -> None:
        response = user_client.get("/api/audit/")
        assert response.status_code == 403

    def test_audit_api_admin_can_list(
        self, admin_client: APIClient, user_client: APIClient
    ) -> None:
        # Generate an audit log via a create
        user_client.post(
            "/api/accounts/",
            {"account_name": "Test ISA", "account_type": "isa"},
        )
        response = admin_client.get("/api/audit/")
        assert response.status_code == 200
        assert response.data["count"] >= 1

    def test_audit_api_filter_by_model_name(
        self, admin_client: APIClient, user_client: APIClient, equity_asset: Asset
    ) -> None:
        # Create an account (generates Account audit log)
        resp = user_client.post(
            "/api/accounts/",
            {"account_name": "Filter Test ISA", "account_type": "isa"},
        )
        account_id = resp.data["id"]

        # Create a holding (generates Holding audit log)
        user_client.post(
            "/api/holdings/",
            {
                "account": account_id,
                "asset": equity_asset.id,
                "quantity": "10.0000",
                "average_cost": "150.0000",
            },
        )

        # Filter for Account only
        response = admin_client.get("/api/audit/?model_name=Account")
        assert response.status_code == 200
        for entry in response.data["results"]:
            assert entry["model_name"] == "Account"


@pytest.mark.django_db
class TestNoAuditOnRead:
    def test_no_audit_log_on_read(
        self, user_client: APIClient, account_obj: Account
    ) -> None:
        initial_count = AuditLog.objects.count()
        user_client.get(f"/api/accounts/{account_obj.id}/")
        assert AuditLog.objects.count() == initial_count
