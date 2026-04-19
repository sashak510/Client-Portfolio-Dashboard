"""Management command to send monthly portfolio summary emails to all active users."""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from apps.accounts.email_service import send_monthly_summary


class Command(BaseCommand):
    help = "Send a monthly portfolio summary email to every active user with a registered email."

    def handle(self, *args, **options) -> None:
        users = User.objects.filter(is_active=True).exclude(email="")
        count = 0
        for user in users:
            try:
                send_monthly_summary(user)
                self.stdout.write(f"  Sent to {user.username} <{user.email}>")
                count += 1
            except Exception as exc:
                self.stderr.write(f"  ERROR for {user.username}: {exc}")
        self.stdout.write(self.style.SUCCESS(f"Done — {count} email(s) sent."))
