# Client Portfolio Dashboard API — Project Write-Up

*A comprehensive guide to discussing this project in interviews and technical assessments.*

---

## 1. Project Overview

**What is it?**

A RESTful API built with Django REST Framework that allows investment advisers to manage client portfolios across multiple asset classes — equities, bonds, and cash. The system supports full CRUD operations, real-time stock pricing via yfinance, JWT-based authentication, and portfolio analytics including allocation breakdowns and gain/loss calculations.

**Why did I build it?**

I wanted to demonstrate my ability to design and build a production-grade backend API using Django, covering authentication, data modelling, business logic separation, third-party API integration, automated testing, and containerised deployment. The financial domain was chosen because it involves real-world complexity — multi-model relationships, decimal precision for monetary values, computed fields, and caching strategies.

---

## 2. Architecture & Design Decisions

### Project Structure

The project follows Django's app-based architecture with two apps:

- **accounts** — handles user registration and JWT authentication
- **portfolio** — contains all business domain logic (clients, assets, holdings, transactions)

Configuration lives in a separate `config/` package, keeping settings, URL routing, and WSGI configuration cleanly separated from application code.

### Why Django REST Framework?

DRF provides a mature, well-documented toolkit for building APIs. Key features I leveraged:

- **ModelViewSet** — gives full CRUD from a single class, reducing boilerplate
- **Serialisers** — handle both input validation and output formatting in one place
- **DefaultRouter** — auto-generates URL patterns following REST conventions
- **Built-in pagination, filtering, and permission classes** — production concerns handled declaratively rather than writing custom middleware

### Service Layer Pattern

Business logic lives in `services.py` rather than in views or serialisers. This is deliberate:

- **PricingService** encapsulates all pricing logic (yfinance calls, caching, fallbacks)
- Views stay thin — they handle HTTP concerns only
- Services are independently testable without needing to make HTTP requests
- If I later swapped yfinance for a different data provider, only the service layer changes

*"If an interviewer asks: 'Why not put the pricing logic in the serialiser?' — the answer is separation of concerns. Serialisers handle data transformation and validation. Business rules like 'fetch a price, cache it for 15 minutes, fall back to the last known price on failure' belong in a service layer."*

---

## 3. Data Model

### Entity Relationship

```
User (Django built-in)
 └── Client (one-to-many: an adviser owns multiple clients)
      ├── Holding (one-to-many: a client has multiple holdings)
      │    └── Asset (many-to-one: each holding references an asset)
      └── Transaction (one-to-many: a client has multiple transactions)
           └── Asset (many-to-one: each transaction references an asset)
```

### Key Model Design Choices

**Client** — has an `owner` foreign key to Django's User model. This is the foundation of data scoping — every query filters by `owner=request.user`, so advisers can never see each other's clients.

**Asset** — uses a single model with an `AssetType` enum (equity/bond/cash) rather than separate tables or inheritance. This keeps the schema simple whilst still allowing type-specific fields:
- Bonds have `face_value`, `coupon_rate`, and `maturity_date` (nullable for non-bonds)
- `last_price` and `price_updated_at` serve as a simple cache layer for live prices

**Holding** — has a `unique_together` constraint on `(client, asset)`, preventing duplicate positions. Tracks `quantity` and `average_cost` for gain/loss calculations.

**Transaction** — records every buy/sell/deposit/withdrawal. The `total_value` field is auto-computed during validation (`quantity × price`). Sell transactions are validated to ensure the quantity doesn't exceed the current holding.

**Why DecimalField everywhere?**

All monetary and quantity fields use `DecimalField`, never `float`. This is critical in financial applications — floating-point arithmetic introduces rounding errors (e.g., `0.1 + 0.2 = 0.30000000000000004` in float). `Decimal` gives exact precision, which is essential when dealing with money.

---

## 4. Authentication & Authorisation

### JWT Authentication (JSON Web Tokens)

The API uses `djangorestframework-simplejwt` for stateless authentication:

1. **Registration** — `POST /api/auth/register/` creates a new user with password validation (passwords must match, minimum 8 characters)
2. **Token Obtain** — `POST /api/auth/token/` returns an access token (60-minute lifetime) and a refresh token (7-day lifetime)
3. **Token Refresh** — `POST /api/auth/token/refresh/` issues a new access token using the refresh token
4. **Authenticated Requests** — clients include `Authorization: Bearer <access_token>` in request headers

*"If an interviewer asks: 'Why JWT instead of session-based auth?' — JWT is stateless. The server doesn't need to store session data, making it horizontally scalable. The token contains the user's identity, cryptographically signed. This is particularly important for APIs consumed by mobile apps or SPAs where traditional cookies don't apply."*

### Data Scoping (Multi-Tenancy)

Every viewset that returns client data overrides `get_queryset()`:

```python
def get_queryset(self):
    return Client.objects.filter(owner=self.request.user)
```

This ensures:
- Adviser A can never see Adviser B's clients, even by guessing IDs
- Holdings and transactions are scoped through the client relationship
- This is tested explicitly in the test suite

---

## 5. Key Features — How They Work

### Live Pricing with Caching

The `PricingService` handles three asset types differently:

| Asset Type | Price Source | Caching |
|-----------|-------------|---------|
| Cash | Always returns `1.0` | No caching needed |
| Bond | Returns `face_value` | No caching needed |
| Equity | Fetches from yfinance | 15-minute cache on the Asset model |

**Caching strategy:** When a price is fetched from yfinance, it's stored on the Asset record (`last_price`, `price_updated_at`). Subsequent requests within 15 minutes return the cached value without hitting the external API. If yfinance fails (network error, rate limiting), the system falls back to the last cached price. If there's no cache at all, it returns `Decimal('0')`.

*"If an interviewer asks about resilience: the system degrades gracefully. A yfinance outage doesn't crash the API — it returns stale prices rather than erroring out."*

### Portfolio Summary Analytics

The `calculate_portfolio_summary()` method computes:

- **Total portfolio value** — sum of (quantity × current price) for all holdings
- **Total gain/loss** — total value minus total cost basis
- **Allocation percentages** — what percentage of the portfolio is in equities, bonds, and cash
- **Top 5 holdings** — sorted by current value, descending

This is exposed via a custom action endpoint: `GET /api/clients/{id}/portfolio-summary/`

### Transaction Validation

The `TransactionSerializer` enforces business rules:

- `total_value` is auto-computed (never trusted from client input)
- Sell transactions validate that the quantity doesn't exceed the current holding
- If no holding exists for the asset being sold, a clear error is returned

---

## 6. API Design

### RESTful URL Structure

```
/api/clients/                          → List/Create
/api/clients/{id}/                     → Retrieve/Update/Delete
/api/clients/{id}/portfolio-summary/   → Custom action (analytics)
/api/clients/{id}/transactions/        → Custom action (filtered list)
/api/assets/                           → List/Create
/api/holdings/                         → List/Create
/api/transactions/                     → List/Create
```

### Filtering

Implemented via `django-filter`:
- Transactions: filter by `client`, `asset`, `transaction_type`, `executed_at` (date range)
- Holdings: filter by `client`, `asset_type`
- Assets: filter by `asset_type`

Example: `GET /api/transactions/?transaction_type=buy&executed_at_after=2025-01-01`

### Pagination

All list endpoints return paginated responses (20 items per page) using DRF's `PageNumberPagination`. Response format:

```json
{
    "count": 45,
    "next": "http://localhost:8000/api/clients/?page=3",
    "previous": "http://localhost:8000/api/clients/?page=1",
    "results": [...]
}
```

### OpenAPI Documentation

The API schema is auto-generated by `drf-spectacular` and served as an interactive Swagger UI at `/api/docs/`. This means the documentation stays in sync with the code — there's no separate spec to maintain.

---

## 7. Testing Strategy

### Test Coverage (23 tests, all passing)

| File | What It Tests |
|------|---------------|
| `test_auth.py` | User registration (happy path + validation), JWT token obtain and refresh |
| `test_models.py` | String representations, unique constraints, field computations |
| `test_views.py` | Full CRUD lifecycle, data scoping between users, portfolio summary structure, transaction validation, filtering by type and date range |
| `test_services.py` | Cash/bond/equity pricing logic, yfinance caching, cache fallback on error, portfolio summary calculations |

### Testing Approach

- **pytest-django** with fixtures — each test gets a clean database
- **`force_authenticate`** — bypasses JWT for view tests (we test JWT separately in `test_auth.py`)
- **`unittest.mock.patch`** — mocks yfinance calls in service tests so tests don't hit external APIs
- **Isolation** — each test is independent; no shared state between tests

*"If an interviewer asks: 'How do you test external API calls?' — I mock them. The `PricingService` tests patch `yfinance.Ticker` to return controlled values, then verify the caching and fallback behaviour works correctly. This keeps tests fast, deterministic, and not dependent on network access."*

---

## 8. Configuration & Deployment

### Environment Management

All secrets and environment-specific settings are managed via `django-environ`:
- `SECRET_KEY` — cryptographic signing key (never hardcoded)
- `DEBUG` — disabled in production
- `ALLOWED_HOSTS` — restricts which domains can serve the app

The `.env.example` file documents required variables. The `.gitignore` excludes `.env` from version control.

### Docker

The project includes a `Dockerfile` and `docker-compose.yml` for containerised deployment:
- Uses `python:3.11-slim` as the base image
- Serves via `gunicorn` (production WSGI server) rather than Django's development server
- Single command to run: `docker-compose up --build`

### Database

SQLite for development (zero configuration). The settings are structured so swapping to PostgreSQL requires only changing the `DATABASES` setting — no code changes needed.

---

## 9. What I'd Add Next

If continuing development:

1. **PostgreSQL** — for production use (concurrent writes, better performance at scale)
2. **Celery + Redis** — for asynchronous price refresh tasks on a schedule rather than on-demand
3. **WebSocket support** — real-time price updates pushed to connected clients
4. **Role-based access control** — admin vs. adviser vs. read-only viewer permissions
5. **CSV/PDF exports** — portfolio report generation
6. **Frontend SPA** — React or Vue dashboard consuming this API
7. **Rate limiting** — protect against API abuse
8. **Audit logging** — track who changed what, when

---

## 10. Common Interview Questions & Answers

**Q: Walk me through what happens when a user creates a new transaction.**

A: The client sends a POST to `/api/transactions/` with a JWT token. DRF authenticates the user, routes to `TransactionViewSet.create()`, which calls `TransactionSerializer.validate()`. The serialiser auto-computes `total_value` from `quantity × price`. If it's a sell, it checks the holding exists and has sufficient quantity. If validation passes, the transaction is saved to the database and the serialised response (with nested asset details) is returned with a 201 status.

**Q: How do you ensure data integrity between holdings and transactions?**

A: The `unique_together` constraint on Holding prevents duplicate positions. Transaction validation checks holding quantities before allowing sells. In a production system, I'd wrap the holding update and transaction creation in a database transaction (`django.db.transaction.atomic`) to ensure atomicity.

**Q: Why did you choose Django over Flask for this project?**

A: Django's ORM, admin panel, and ecosystem (DRF, django-filter, SimpleJWT) provide more out of the box for a data-heavy API. Flask gives more flexibility but requires assembling these components manually. For a CRUD-heavy financial API with relationships between models, Django's batteries-included approach is more productive.

**Q: How would you handle this at scale?**

A: Move to PostgreSQL, add connection pooling (pgbouncer), implement Redis caching for frequently accessed portfolios, use Celery for background price refreshes, add database indices on frequently filtered fields, and consider read replicas if read traffic dominates.

**Q: What security considerations did you address?**

A: JWT tokens with short-lived access tokens (60 minutes) and longer refresh tokens (7 days). All endpoints require authentication by default. Data is scoped per user at the queryset level — not just at the URL level — so even guessing IDs won't leak data. Secrets are externalised via environment variables. Django's built-in protections handle CSRF, XSS, SQL injection, and clickjacking.

---

## 11. Technologies Used — Quick Reference

| Technology | Purpose | Why This Choice |
|-----------|---------|-----------------|
| Django 5.x | Web framework | Batteries-included, mature ORM, admin panel |
| Django REST Framework | API toolkit | Industry standard for Django APIs |
| SimpleJWT | Authentication | Stateless, scalable, widely adopted |
| yfinance | Live stock prices | Free, no API key needed, covers major exchanges |
| django-filter | Query filtering | Declarative filtering with minimal code |
| drf-spectacular | API documentation | Auto-generates OpenAPI 3.0 from code |
| pytest | Testing | Cleaner syntax than unittest, powerful fixtures |
| django-environ | Configuration | 12-factor app compliance, clean settings |
| Docker | Containerisation | Reproducible builds, deployment consistency |
| SQLite | Development database | Zero configuration, swappable to PostgreSQL |
