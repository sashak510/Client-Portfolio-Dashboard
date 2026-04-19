"""Views for user registration and cookie-based JWT auth."""

from django.contrib.auth.models import User
from django.middleware.csrf import get_token
from rest_framework import generics, permissions
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError, InvalidToken
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView as _BaseTokenObtainPairView

from django.conf import settings

from apps.accounts.serializers import RegisterSerializer


def _cookie_kwargs(secure: bool) -> dict:
    """Return shared kwargs for set_cookie calls."""
    return {
        "httponly": True,
        "secure": secure,
        "samesite": "Lax",
    }


class RegisterView(generics.CreateAPIView):
    """Register a new user account."""

    serializer_class = RegisterSerializer
    permission_classes = (permissions.AllowAny,)

    def create(self, request, *args, **kwargs) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
            },
            status=201,
        )


class CookieTokenObtainPairView(APIView):
    """Login: validate credentials, set JWT access + refresh as HttpOnly cookies."""

    permission_classes = (permissions.AllowAny,)

    def post(self, request: Request, *args, **kwargs) -> Response:
        # Delegate credential validation to simplejwt's serializer.
        from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

        serializer = TokenObtainPairSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            raise InvalidToken(exc.args[0])

        secure = not settings.DEBUG
        cookie_kw = _cookie_kwargs(secure)

        response = Response({"detail": "Login successful."})
        response.set_cookie(
            "access_token",
            serializer.validated_data["access"],
            max_age=int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()),
            **cookie_kw,
        )
        response.set_cookie(
            "refresh_token",
            serializer.validated_data["refresh"],
            max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
            **cookie_kw,
        )
        # Issue CSRF cookie so the frontend can echo it back on mutating requests.
        get_token(request)
        return response


class CookieTokenRefreshView(APIView):
    """Refresh: read refresh token from cookie, issue new access token cookie."""

    permission_classes = (permissions.AllowAny,)

    def post(self, request: Request, *args, **kwargs) -> Response:
        refresh_value = request.COOKIES.get("refresh_token")
        if not refresh_value:
            return Response({"detail": "Refresh token not found."}, status=401)

        try:
            refresh = RefreshToken(refresh_value)
        except TokenError as exc:
            return Response({"detail": str(exc)}, status=401)

        secure = not settings.DEBUG
        cookie_kw = _cookie_kwargs(secure)

        response = Response({"detail": "Token refreshed."})
        response.set_cookie(
            "access_token",
            str(refresh.access_token),
            max_age=int(settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"].total_seconds()),
            **cookie_kw,
        )
        return response


class LogoutView(APIView):
    """Logout: clear auth cookies."""

    permission_classes = (permissions.AllowAny,)

    def post(self, request: Request, *args, **kwargs) -> Response:
        response = Response({"detail": "Logged out."})
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        return response


class MeView(APIView):
    """Return or update basic info about the currently authenticated user."""

    def get(self, request: Request, *args, **kwargs) -> Response:
        from apps.accounts.models import UserProfile
        user = request.user
        profile, _ = UserProfile.objects.get_or_create(user=user)
        return Response({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "region": profile.region,
        })

    def patch(self, request: Request, *args, **kwargs) -> Response:
        from apps.accounts.models import UserProfile
        user = request.user
        username = request.data.get("username")
        email = request.data.get("email")
        region = request.data.get("region")
        if username:
            if User.objects.exclude(pk=user.pk).filter(username=username).exists():
                return Response({"detail": "Username already taken."}, status=400)
            user.username = username
        if email is not None:
            user.email = email
        user.save()
        if region is not None:
            from apps.accounts.models import UserProfile
            valid_regions = [r.value for r in UserProfile.Region]
            if region not in valid_regions:
                return Response({"detail": f"Invalid region. Choose from: {', '.join(valid_regions)}."}, status=400)
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.region = region
            profile.save()
        profile, _ = UserProfile.objects.get_or_create(user=user)
        return Response({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "region": profile.region,
        })

    def delete(self, request: Request, *args, **kwargs) -> Response:
        user = request.user
        response = Response({"detail": "Account deleted."}, status=200)
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        user.delete()
        return response


class ChangePasswordView(APIView):
    """Change the authenticated user's password."""

    def post(self, request: Request, *args, **kwargs) -> Response:
        user = request.user
        current = request.data.get("current_password", "")
        new_pw = request.data.get("new_password", "")
        if not user.check_password(current):
            return Response({"detail": "Current password is incorrect."}, status=400)
        if len(new_pw) < 8:
            return Response({"detail": "New password must be at least 8 characters."}, status=400)
        user.set_password(new_pw)
        user.save()
        return Response({"detail": "Password changed successfully."})


class SendMonthlySummaryView(APIView):
    """Send a monthly portfolio summary email to the authenticated user — POST /api/auth/send-monthly-summary/."""

    def post(self, request: Request, *args, **kwargs) -> Response:
        from apps.accounts.email_service import send_monthly_summary

        try:
            send_monthly_summary(request.user)
        except Exception as exc:
            return Response({"detail": f"Failed to send email: {exc}"}, status=500)
        return Response({"detail": "Summary email sent."}, status=200)
