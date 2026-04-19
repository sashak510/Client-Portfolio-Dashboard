# Stasha Frontend

A lightweight, single-page dashboard for the Stasha personal finance API. Built with vanilla HTML, CSS, and JavaScript — no frameworks, no build step.

<!-- Add screenshot here -->

## Prerequisites

- The Django API must be running on `http://localhost:8000`
- CORS must be configured on the API (see [CORS_SETUP.md](CORS_SETUP.md))
- Seed data should be loaded (`python manage.py seed_data`)

## How to Run

**Option 1 — Open directly:**

Double-click `index.html` in your file browser, or open it in a browser.

**Option 2 — Local server (recommended):**

```bash
chmod +x serve.sh
./serve.sh
```

Then visit `http://localhost:5500`.

## Default Login

- **Username:** `adviser1`
- **Password:** `testpass123`

## Features

- JWT authentication with automatic token refresh
- Dashboard with your accounts and total portfolio value
- Account detail view with portfolio summary, allocation chart, holdings, and transactions
- Asset registry view
- Responsive design — works on mobile
- Professional fintech-style design system
