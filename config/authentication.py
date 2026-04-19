"""Custom DRF authentication: read JWT access token from HttpOnly cookie."""

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken, TokenError


class CookieJWTAuthentication(JWTAuthentication):
    """Authenticate by reading the JWT access token from the ``access_token`` cookie.

    Falls back to the standard ``Authorization: Bearer …`` header so existing
    clients (e.g. the browsable API / Swagger UI) continue to work.
    """

    def authenticate(self, request):
        # Prefer the cookie; fall back to the Authorization header.
        raw_token = request.COOKIES.get("access_token")

        if raw_token is None:
            # Let the parent class try the Authorization header.
            return super().authenticate(request)

        try:
            validated_token = self.get_validated_token(raw_token)
        except TokenError as exc:
            raise InvalidToken(exc.args[0])

        return self.get_user(validated_token), validated_token
