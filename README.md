# PortfolioDash

A production-ready REST API for managing multi-asset investment portfolios, built with Django REST Framework.

![CI](https://github.com/sashak510/Client-Portfolio-Dashboard/actions/workflows/ci.yml/badge.svg)
![Python 3.11](https://img.shields.io/badge/python-3.11-blue?logo=python&logoColor=white)
![Django 5](https://img.shields.io/badge/django-5.x-092E20?logo=django&logoColor=white)
![License MIT](https://img.shields.io/badge/license-MIT-green)

---

## Overview

PortfolioDash is a multi-tenant portfolio management API built for financial advisors who need to track client investments across equities, bonds, and cash. Each advisor sees only their own clients; holdings are priced in real time via yfinance with a staleness-aware cache layer. The project demonstrates DRF best practices — service layer architecture, scoped querysets, Decimal precision for all monetary values, JWT authentication, and a comprehensive pytest suite with all external dependencies mocked.

---

## Features

- **Multi-asset portfolio tracking** — equities, bonds, and cash in a single unified model
- **JWT authentication** — register, obtain tokens, refresh on expiry
- **Live stock pricing** — yfinance integration with per-asset cache; stale prices trigger a background refresh
- **Portfolio analytics** — allocation by asset class (%), unrealised gain/loss, top holdings
- **Transaction validation** — sell orders are rejected when quantity exceeds current holding
- **Filtering and pagination** — filter transactions by type, date range, client; paginated list responses
- **Auto-generated API docs** — OpenAPI 3.0 schema + Swagger UI via drf-spectacular
- **Docker-ready** — single `docker-compose up --build` to run locally
- **23+ tests** — models, services, and views; no real network calls in CI

---

## Tech Stack

| Category   | Tool                          |
|------------|-------------------------------|
| Framework  | Django 5.x                    |
| API        | Django REST Framework         |
| Auth       | SimpleJWT                     |
| Pricing    | yfinance                      |
| Filtering  | django-filter                 |
| Docs       | drf-spectacular               |
| Testing    | pytest + pytest-django        |
| Config     | django-environ                |
| Server     | gunicorn                      |
| Container  | Docker                        |

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/sashak510/Client-Portfolio-Dashboard.git
cd Client-Portfolio-Dashboard

# 2. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env             # edit SECRET_KEY and ALLOWED_HOSTS as needed

# 5. Apply migrations
python manage.py migrate

# 6. Seed sample data
python manage.py seed_data

# 7. Start the development server
python manage.py runserver
```

Visit [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/) for the interactive API explorer.

---

## Docker Quick Start

```bash
cp .env.example .env
docker-compose up --build
```

The API will be available at [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/).

---

## API Endpoints

| Method              | Endpoint                              | Description                        | Auth |
|---------------------|---------------------------------------|------------------------------------|------|
| `POST`              | `/api/auth/register/`                 | Register a new advisor account     | No   |
| `POST`              | `/api/auth/token/`                    | Obtain access + refresh token pair | No   |
| `POST`              | `/api/auth/token/refresh/`            | Refresh an expired access token    | No   |
| `GET / POST`        | `/api/clients/`                       | List clients / create a client     | Yes  |
| `GET`               | `/api/clients/{id}/`                  | Retrieve a client                  | Yes  |
| `PUT / PATCH`       | `/api/clients/{id}/`                  | Update a client                    | Yes  |
| `DELETE`            | `/api/clients/{id}/`                  | Delete a client                    | Yes  |
| `GET`               | `/api/clients/{id}/portfolio-summary/`| Allocation, gain/loss, top holdings| Yes  |
| `GET / POST`        | `/api/assets/`                        | List assets / create an asset      | Yes  |
| `GET / PUT / DELETE`| `/api/assets/{id}/`                   | Asset detail / update / delete     | Yes  |
| `GET / POST`        | `/api/holdings/`                      | List holdings / create a holding   | Yes  |
| `GET / PUT / DELETE`| `/api/holdings/{id}/`                 | Holding detail / update / delete   | Yes  |
| `GET / POST`        | `/api/transactions/`                  | List transactions / record one     | Yes  |
| `GET / PUT / DELETE`| `/api/transactions/{id}/`             | Transaction detail / update / delete | Yes |
| `GET`               | `/api/schema/`                        | Raw OpenAPI 3.0 spec (JSON/YAML)   | No   |
| `GET`               | `/api/docs/`                          | Swagger UI                         | No   |
| `GET`               | `/health/`                            | Health check                       | No   |

---

## Authentication Flow

1. **Register** — `POST /api/auth/register/` with `username`, `email`, `password`, `password_confirm`
2. **Get tokens** — `POST /api/auth/token/` with `username` + `password`; response contains `access` and `refresh`
3. **Authenticate requests** — add `Authorization: Bearer <access_token>` to every protected request
4. **Refresh** — when the access token expires, `POST /api/auth/token/refresh/` with `{"refresh": "<token>"}`

```bash
# Get a token pair
curl -X POST http://localhost:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "advisor1", "password": "testpass123"}'

# Use the access token
curl http://localhost:8000/api/clients/ \
  -H "Authorization: Bearer <access_token>"
```

---

## Running Tests

```bash
pytest --tb=short -q
```

The suite contains 23+ tests covering models, the PricingService, and all API views. All yfinance calls are mocked — the test run makes no real network requests and requires no API keys.

---

## API Documentation

With the server running, visit [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/) for the Swagger UI. Run `python manage.py seed_data` first so the explorer has meaningful data to browse. The raw OpenAPI spec is available at `/api/schema/`.

---

## Project Structure

```
Client-Portfolio-Dashboard/
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── pytest.ini
├── .github/
│   └── workflows/
│       └── ci.yml
├── config/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── apps/
    ├── accounts/
    │   ├── models.py
    │   ├── serializers.py
    │   ├── views.py
    │   ├── urls.py
    │   └── tests/
    │       └── test_auth.py
    └── portfolio/
        ├── models.py
        ├── serializers.py
        ├── views.py
        ├── urls.py
        ├── filters.py
        ├── services.py
        ├── management/
        │   └── commands/
        │       └── seed_data.py
        └── tests/
            ├── test_models.py
            ├── test_views.py
            └── test_services.py
```

---

## Design Decisions

- **PricingService abstraction** — yfinance is isolated behind a single service class. Swapping to a paid data provider or adding Redis caching requires changes in exactly one place, with no view or serializer edits.
- **Decimal fields for all monetary values** — floats accumulate rounding error over repeated arithmetic. Every price, quantity, and total is stored as `DecimalField` — a hard requirement for financial data.
- **Scoped querysets** — `ClientViewSet` filters `Client.objects.all()` to `owner=request.user` before any other filter or pagination runs. Advisors have no query path to another advisor's data, by construction rather than by convention.
- **Cached pricing with staleness check** — `PricingService.get_current_price()` returns the cached `last_price` if it was fetched within the threshold, falls back to the cached value on network error, and only calls yfinance when the cache is stale. This avoids hammering the external API on every portfolio summary request.

---

## Seed Data

```bash
python manage.py seed_data
```

Creates a realistic dataset ready for exploration:

- **Users**: `admin` / `admin` (superuser), `advisor1` / `testpass123`
- **Assets**: AAPL, MSFT, VOO (equities), US-TBOND-10Y (bond), GBP-CASH (cash)
- **Clients**: 3 clients owned by `advisor1`
- **Holdings**: a mix of asset types across each client
- **Transactions**: 13 realistic buy/sell transactions spread over the past 6 months

---

## Future Improvements

- Frontend dashboard (React) consuming this API
- WebSocket endpoint for live price streaming
- Celery + Redis for async price refresh on a schedule
- PostgreSQL for production (swap `DATABASE_URL` in `.env`)
- Per-advisor rate limiting on the pricing endpoints
- Audit log for transaction history (immutable event trail)
