# CORS Setup for PortfolioDash Frontend

The Django API needs CORS headers so the frontend can make requests from a different origin.

## Steps

1. Install django-cors-headers:

```bash
pip install django-cors-headers
```

2. Add `'corsheaders'` to `INSTALLED_APPS` in `config/settings.py`:

```python
INSTALLED_APPS = [
    # ...existing apps...
    'corsheaders',
]
```

3. Add `'corsheaders.middleware.CorsMiddleware'` to `MIDDLEWARE` in `config/settings.py`, **before** `CommonMiddleware`:

```python
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # <-- add this line
    'django.middleware.common.CommonMiddleware',
    # ...rest of middleware...
]
```

4. Add allowed origins to `config/settings.py`:

```python
CORS_ALLOWED_ORIGINS = [
    'http://127.0.0.1:5500',
    'http://localhost:5500',
]

# If opening index.html directly from the filesystem (file:// protocol),
# the browser sends Origin: null. You must also allow that:
CORS_ALLOW_ALL_ORIGINS = True  # or add 'null' to the list above (not recommended for production)
```

> **Note:** For local development only. In production, set `CORS_ALLOWED_ORIGINS` to your actual frontend domain and set `CORS_ALLOW_ALL_ORIGINS = False`.
