# Client Portfolio Dashboard API

A multi-asset portfolio tracker API built with Django REST Framework. Advisers manage clients and their investment holdings across stocks, bonds, and cash with live pricing and analytics.

## Features

- Multi-asset portfolio management (equities, bonds, cash)
- JWT authentication for secure API access
- Live stock price lookups via yfinance with caching
- Portfolio analytics: allocation breakdown, gain/loss calculations
- Full CRUD for clients, assets, holdings, and transactions
- OpenAPI 3.0 documentation with Swagger UI
- Filtering, searching, and pagination
- Docker support for containerised deployment

## Tech Stack

- **Django 5.x** + **Django REST Framework**
- **yfinance** for live equity pricing
- **SimpleJWT** for authentication
- **drf-spectacular** for OpenAPI docs
- **django-filter** for queryset filtering
- **pytest + pytest-django** for testing
- **SQLite** (dev) with clear path to PostgreSQL

## Quick Start

```bash
# Clone and enter the project
cd "Client Portfolio Dashboard"

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env

# Run migrations and seed data
python manage.py migrate
python manage.py seed_data

# Start the server
python manage.py runserver
```

## Docker Quick Start

```bash
cp .env.example .env
docker-compose up --build
```

## API Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/api/auth/register/` | Register a new user | No |
| POST | `/api/auth/token/` | Obtain JWT token pair | No |
| POST | `/api/auth/token/refresh/` | Refresh access token | No |
| GET/POST | `/api/clients/` | List/create clients | Yes |
| GET/PUT/PATCH/DELETE | `/api/clients/{id}/` | Client detail/update/delete | Yes |
| GET | `/api/clients/{id}/portfolio-summary/` | Portfolio analytics | Yes |
| GET | `/api/clients/{id}/transactions/` | Client's transactions (filterable) | Yes |
| GET/POST | `/api/assets/` | List/create assets | Yes |
| GET/PUT/PATCH/DELETE | `/api/assets/{id}/` | Asset detail/update/delete | Yes |
| GET/POST | `/api/holdings/` | List/create holdings | Yes |
| GET/PUT/PATCH/DELETE | `/api/holdings/{id}/` | Holding detail/update/delete | Yes |
| GET/POST | `/api/transactions/` | List/create transactions | Yes |
| GET/PUT/PATCH/DELETE | `/api/transactions/{id}/` | Transaction detail/update/delete | Yes |
| GET | `/api/docs/` | Swagger UI documentation | No |
| GET | `/api/schema/` | OpenAPI 3.0 schema | No |
| GET | `/health/` | Health check | No |

## Running Tests

```bash
pytest
```

## API Documentation

Once the server is running, visit [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/) for interactive Swagger UI documentation.

## Project Structure

```
Client Portfolio Dashboard/
├── manage.py
├── requirements.txt
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── pytest.ini
├── config/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── accounts/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── tests/
│   │       └── test_auth.py
│   └── portfolio/
│       ├── models.py
│       ├── serializers.py
│       ├── views.py
│       ├── urls.py
│       ├── filters.py
│       ├── services.py
│       ├── management/commands/seed_data.py
│       └── tests/
│           ├── test_models.py
│           ├── test_views.py
│           └── test_services.py
```

## Seed Data

Run `python manage.py seed_data` to populate:
- **Users**: `admin/admin` (superuser), `adviser1/testpass123`
- **Assets**: AAPL, MSFT, VOO (equities), US-TBOND-10Y (bond), GBP-CASH (cash)
- **Clients**: 3 clients owned by adviser1
- **Holdings**: Mix of asset types per client
- **Transactions**: 13 realistic transactions over the past 6 months

## Future Improvements

- WebSocket support for real-time price updates
- PostgreSQL for production database
- Celery for async price refresh tasks
- Frontend SPA (React/Vue) dashboard
- Role-based access control (admin vs. adviser vs. read-only)
- CSV/PDF portfolio report exports
