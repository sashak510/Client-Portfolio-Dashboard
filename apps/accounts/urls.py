"""URL routing for authentication endpoints."""

from django.urls import path

from apps.accounts.views import (
    ChangePasswordView,
    CookieTokenObtainPairView,
    CookieTokenRefreshView,
    LogoutView,
    MeView,
    RegisterView,
    SendMonthlySummaryView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("token/", CookieTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", CookieTokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("send-monthly-summary/", SendMonthlySummaryView.as_view(), name="send-monthly-summary"),
]
