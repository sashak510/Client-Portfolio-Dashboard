"""Management command to take a portfolio snapshot for all active users."""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from apps.portfolio.views import _build_snapshot_for_user


class Command(BaseCommand):
    help = "Record today's portfolio snapshot for all active users (idempotent — updates if already exists)."

    def handle(self, *args, **options) -> None:
        users = User.objects.filter(is_active=True)
        count = 0
        for user in users:
            try:
                snapshot = _build_snapshot_for_user(user)
                self.stdout.write(
                    f"  {user.username}: £{snapshot.total_value} on {snapshot.date}"
                )
                count += 1
            except Exception as exc:
                self.stderr.write(f"  ERROR for {user.username}: {exc}")
        self.stdout.write(self.style.SUCCESS(f"Done — {count} snapshot(s) saved."))
