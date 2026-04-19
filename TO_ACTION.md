# To Action

## Switch auth to httpOnly cookie sessions

**Problem:** Page refresh logs the user out. Tokens live in JS memory only ([frontend/app.js:11-12](frontend/app.js#L11-L12)), so a refresh wipes them.

**Chosen fix:** Move JWTs into `HttpOnly; Secure; SameSite=Lax` cookies. More secure than `localStorage` (immune to XSS token theft) and survives refresh.

### Backend — `config/`, `apps/accounts/`

- [ ] Add custom login/logout/refresh/me endpoints in [apps/accounts/views.py](apps/accounts/views.py) that set JWT access + refresh as `HttpOnly; Secure; SameSite=Lax` cookies instead of returning them in the JSON body.
- [ ] Add a cookie-reading JWT auth class (subclass `rest_framework_simplejwt.authentication.JWTAuthentication`, read token from `request.COOKIES` instead of the `Authorization` header). Wire it as the default in `REST_FRAMEWORK.DEFAULT_AUTHENTICATION_CLASSES` in [config/settings.py](config/settings.py).
- [ ] Update [apps/accounts/urls.py](apps/accounts/urls.py) to point `token/` and `token/refresh/` at the new cookie-setting views; add `logout/` and `me/`.
- [ ] Enable CSRF protection on auth + mutating endpoints. Issue CSRF cookie on login. Frontend echoes it back via `X-CSRFToken` header on POST/PATCH/DELETE.
- [ ] Set `CORS_ALLOW_CREDENTIALS = True` in [config/settings.py](config/settings.py) so the browser sends cookies cross-origin (`localhost:5500` → `localhost:8000`).
- [ ] Gate `Secure=True` on `not DEBUG` so cookies still work over plain `http://localhost` during dev.

### Frontend — `frontend/app.js`

- [ ] Remove `accessToken` / `refreshToken` variables and every `Authorization: Bearer …` header.
- [ ] Add `credentials: 'include'` to every `fetch` call so cookies are sent.
- [ ] On page load, call `GET /api/auth/me/`. 200 → skip login panel and load dashboard. 401 → show login.
- [ ] Read the `csrftoken` cookie and send it as `X-CSRFToken` on mutating requests.
- [ ] Fix the hand-rolled `Authorization` header on the CSV upload at [frontend/app.js:1234](frontend/app.js#L1234).

### Tradeoffs / notes

- Cross-origin `localhost:5500` ↔ `localhost:8000`: `SameSite=Lax` is fine since the frontend fetches the API directly (no third-party context).
- `Secure` cookies don't round-trip over plain HTTP in some browsers — dev uses `Secure=False`, prod uses `Secure=True`.
- CSRF adds one round-trip (read cookie, echo header). Small amount of plumbing.

**Size:** ~150 lines backend, ~40 lines frontend.
