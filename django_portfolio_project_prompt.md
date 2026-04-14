# Prompt: Client Portfolio Dashboard API


---

## THE PROMPT

You are helping me build a complete, production-ready Django REST Framework project called **/Users/sashakarniyuk/aws-projects/Client Portfolio Dashboard** — a Client Portfolio Dashboard API. I am an experienced Python developer (Flask, OCR tools, API integrations, Power BI) but new to Django. Generate every file I need to have a working, testable, deployable project.

### Project Overview

A multi-asset portfolio tracker API. Users (advisors) manage clients and their investment holdings across stocks, bonds, and cash. The API supports full CRUD, portfolio valuation with live stock prices via yfinance, and summary analytics (allocation breakdown, gain/loss).

---

### Tech Stack & Dependencies

- **Python 3.11+**
- **Django 5.x**
- **Django REST Framework 3.15+**
- **djangorestframework-simplejwt** for JWT authentication
- **django-filter** for queryset filtering
- **drf-spectacular** for OpenAPI 3.0 schema + Swagger UI
- **yfinance** for live stock price lookups
- **pytest + pytest-django** for testing
- **django-environ** for environment variable management
- **gunicorn** for production server
- **Docker + docker-compose** for containerisation
- **SQLite** for development, with a clear path to swap to PostgreSQL

---

### Project Structure

Generate this exact layout:

```
/Users/sashakarniyuk/aws-projects/Client Portfolio Dashboard/
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── README.md
├── pytest.ini (or pyproject.toml with pytest config)
├── config/
│   ├── __init__.py
│   ├── settings.py        # Uses django-environ, splits DEBUG/SECRET_KEY/ALLOWED_HOSTS to env vars
│   ├── urls.py             # Includes API router + spectacular URLs
│   └── wsgi.py
├── apps/
│   ├── __init__.py
│   ├── accounts/           # User/auth related
│   │   ├── __init__.py
│   │   ├── models.py       # Extend or proxy Django's User if needed
│   │   ├── serializers.py  # Registration + user serializer
│   │   ├── views.py        # Register endpoint
│   │   ├── urls.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       └── test_auth.py
│   └── portfolio/
│       ├── __init__.py
│       ├── models.py
│       ├── serializers.py
│       ├── views.py
│       ├── urls.py
│       ├── filters.py
│       ├── services.py     # PricingService lives here
│       ├── management/
│       │   └── commands/
│       │       └── seed_data.py
│       └── tests/
│           ├── __init__.py
│           ├── test_models.py
│           ├── test_views.py
│           └── test_services.py
```

---

### Models (apps/portfolio/models.py)

```python
class Client(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='clients')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class Asset(models.Model):
    class AssetType(models.TextChoices):
        EQUITY = 'equity', 'Equity'
        BOND = 'bond', 'Bond'
        CASH = 'cash', 'Cash'

    symbol = models.CharField(max_length=10, unique=True)  # e.g., AAPL, US10Y, GBP
    name = models.CharField(max_length=200)
    asset_type = models.CharField(max_length=10, choices=AssetType.choices)
    # Bond-specific (nullable for non-bonds)
    face_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    coupon_rate = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    maturity_date = models.DateField(null=True, blank=True)
    # Cached pricing
    last_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    price_updated_at = models.DateTimeField(null=True, blank=True)

class Holding(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='holdings')
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='holdings')
    quantity = models.DecimalField(max_digits=14, decimal_places=4)
    average_cost = models.DecimalField(max_digits=12, decimal_places=4)

    class Meta:
        unique_together = ('client', 'asset')

class Transaction(models.Model):
    class TransactionType(models.TextChoices):
        BUY = 'buy', 'Buy'
        SELL = 'sell', 'Sell'
        DEPOSIT = 'deposit', 'Deposit'
        WITHDRAW = 'withdraw', 'Withdraw'

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='transactions')
    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TransactionType.choices)
    quantity = models.DecimalField(max_digits=14, decimal_places=4)
    price = models.DecimalField(max_digits=12, decimal_places=4)
    total_value = models.DecimalField(max_digits=14, decimal_places=2)  # quantity * price
    note = models.TextField(blank=True)
    executed_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
```

---

### Serializers (apps/portfolio/serializers.py)

- **AssetSerializer**: All fields. Read-only on last_price and price_updated_at.
- **HoldingSerializer**: Nested read of asset (symbol + name + asset_type). Include a computed `current_value` field (quantity × last_price) and `gain_loss` field (current_value - quantity × average_cost). Writable via asset ID.
- **TransactionSerializer**: Validate that sell quantity does not exceed current holding. Auto-compute `total_value`. Nested read of asset.
- **ClientSerializer**: Basic fields. Include a `total_portfolio_value` as a SerializerMethodField that sums all holding current values.
- **ClientDetailSerializer**: Extends ClientSerializer with nested holdings list and recent transactions (last 10).
- **PortfolioSummarySerializer**: Read-only. Returns: total_value, cash_allocation_pct, equity_allocation_pct, bond_allocation_pct, top_holdings (top 5 by value), total_gain_loss.

---

### Views (apps/portfolio/views.py)

Use `ModelViewSet` for Client, Asset, Holding, Transaction. Register all with a DRF `DefaultRouter`.

**Custom actions:**
- `GET /api/clients/{id}/portfolio-summary/` → Returns PortfolioSummarySerializer data.
- `GET /api/clients/{id}/transactions/` → Filterable transaction list (by asset, type, date range).

**Filtering (via django-filter):**
- Transactions: filter by `client`, `asset`, `transaction_type`, `executed_at` (range).
- Holdings: filter by `client`, `asset__asset_type`.
- Assets: filter by `asset_type`.

**Permissions:**
- All endpoints require authentication (IsAuthenticated).
- Clients are scoped to the requesting user (owner field) — override `get_queryset()` to filter by `request.user`.
- Holdings and Transactions are scoped through the client relationship.

**Pagination:**
- Use `PageNumberPagination` with `page_size=20` as the project default.

---

### Services (apps/portfolio/services.py)

```python
class PricingService:
    CACHE_TTL_MINUTES = 15

    @staticmethod
    def get_current_price(asset: Asset) -> Decimal:
        """
        Returns the current price for an asset.
        - Equities: fetch from yfinance, cache on the Asset model.
        - Bonds: return face_value.
        - Cash: return Decimal('1.0').
        If yfinance fails, return the last cached price. If no cache, return 0.
        """

    @staticmethod
    def refresh_prices(assets: QuerySet) -> dict:
        """Bulk refresh prices for a queryset of assets. Returns {symbol: price}."""

    @staticmethod
    def calculate_portfolio_summary(client: Client) -> dict:
        """Returns the full portfolio summary dict for a client."""
```

Implement these fully. Use `yfinance.Ticker(symbol).info.get('currentPrice')` or `fast_info['lastPrice']` with a try/except fallback. Use `timezone.now()` for cache staleness checks.

---

### Seed Data Command (apps/portfolio/management/commands/seed_data.py)

Create a management command `python manage.py seed_data` that populates:
- 1 superuser (admin/admin)
- 1 regular user (advisor1/testpass123)
- 5 assets: AAPL (equity), MSFT (equity), VOO (equity), US-TBOND-10Y (bond, face_value=1000, coupon_rate=0.0425), GBP-CASH (cash)
- 3 clients owned by advisor1
- Realistic holdings for each client (mix of asset types)
- 10-15 transactions spread across clients with realistic dates over the past 6 months
- Make it idempotent (check if data exists before creating)

---

### Authentication (apps/accounts/)

- Use `djangorestframework-simplejwt`.
- Endpoints: `POST /api/auth/register/` (create user), `POST /api/auth/token/` (obtain JWT pair), `POST /api/auth/token/refresh/` (refresh).
- Registration serializer: username, email, password, password_confirm. Validate passwords match.

---

### URL Configuration (config/urls.py)

```
/api/                     → DRF router (clients, assets, holdings, transactions)
/api/auth/                → Auth URLs (register, token, token/refresh)
/api/schema/              → drf-spectacular schema
/api/docs/                → Swagger UI (SpectacularSwaggerView)
/admin/                   → Django admin
/health/                  → Simple health check (return 200 + {"status": "ok"})
```

---

### Settings (config/settings.py)

Use `django-environ` to load from `.env`. Include:
- `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` from env vars
- DRF config: default authentication (JWT), default permission (IsAuthenticated), default pagination, default filter backends (DjangoFilterBackend, SearchFilter, OrderingFilter)
- SPECTACULAR settings with title "/Users/sashakarniyuk/aws-projects/Client Portfolio Dashboard API", version "1.0.0"
- SIMPLE_JWT config with 60-minute access token, 7-day refresh token

---

### Tests

Write tests using `pytest-django` with `@pytest.fixture` and `api_client` (DRF's APIClient). Use `@pytest.mark.django_db`.

**test_auth.py:**
- Test registration (happy path + password mismatch)
- Test login returns access + refresh tokens

**test_models.py:**
- Test Client string representation
- Test Holding unique_together constraint
- Test Transaction total_value computation

**test_views.py:**
- Test CRUD on clients (create, list, retrieve, update, delete)
- Test that user A cannot see user B's clients
- Test portfolio summary endpoint returns expected structure
- Test transaction validation (can't sell more than held)
- Test filtering on transactions by type and date range

**test_services.py:**
- Test PricingService returns Decimal('1.0') for cash
- Test PricingService returns face_value for bonds
- Mock yfinance and test equity price fetch + caching
- Test portfolio summary calculation

Use `unittest.mock.patch` to mock yfinance calls in tests.

---

### Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python manage.py collectstatic --noinput 2>/dev/null || true
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
```

### docker-compose.yml

Single service for now (web). Mount `.env`. Expose port 8000.

---

### .env.example

```
SECRET_KEY=change-me-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

---

### .gitignore

Standard Python/Django gitignore: `__pycache__`, `*.pyc`, `.env`, `db.sqlite3`, `.venv`, `staticfiles/`, `*.egg-info`, `.pytest_cache`.

---

### README.md

Write a professional README with these sections:
1. **Project Title + one-line description**
2. **Features** (bullet list: multi-asset portfolios, JWT auth, live pricing, OpenAPI docs, Docker support)
3. **Tech Stack** (Django, DRF, yfinance, SimpleJWT, drf-spectacular, pytest)
4. **Quick Start** — step-by-step: clone, create venv, install requirements, copy .env, migrate, seed data, run server
5. **Docker Quick Start** — docker-compose up
6. **API Endpoints** — table of all endpoints with method, path, description, auth required
7. **Running Tests** — `pytest` command
8. **API Documentation** — link to /api/docs/ when running locally
9. **Project Structure** — tree view
10. **Future Improvements** — WebSocket price updates, PostgreSQL, celery for async price refresh, frontend SPA

---

### Code Quality Requirements

- Type hints on all function signatures
- Docstrings on all services, views, and non-trivial methods
- No hardcoded secrets — everything through django-environ
- All monetary fields use `DecimalField`, never float
- All custom validation in serializers with clear error messages
- Consistent API error response format: `{"detail": "error message"}`

---

### IMPORTANT INSTRUCTIONS

1. Generate EVERY file with COMPLETE code — no placeholders, no "add more here", no TODOs.
2. All imports must be correct and complete.
3. The project must run with `python manage.py migrate && python manage.py seed_data && python manage.py runserver` with zero errors.
4. Tests must pass with `pytest` with zero errors.
5. Every endpoint must be testable via the browsable API at /api/docs/.
