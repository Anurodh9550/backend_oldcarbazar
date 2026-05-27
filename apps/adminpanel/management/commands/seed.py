"""Seed default admin operators + app settings.

Run automatically on every Render deploy via ``build.sh``. Idempotent — safe
to re-run; only creates the row when an admin with the same email doesn't
exist yet. Existing admins are NOT overwritten so a production password
change is not undone by the next deploy.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.adminpanel.models import Admin, AppSettings


SEED_ADMINS = [
    {
        "email": "admin@oldcarbazar.com",
        "password": "admin@123",
        "name": "Anurodh Singh",
        "role": Admin.Role.SUPER_ADMIN,
    },
    {
        "email": "moderator@oldcarbazar.com",
        "password": "mod@123",
        "name": "Riya Sharma",
        "role": Admin.Role.MODERATOR,
    },
    {
        "email": "support@oldcarbazar.com",
        "password": "support@123",
        "name": "Karan Mehta",
        "role": Admin.Role.SUPPORT,
    },
]


class Command(BaseCommand):
    help = "Seed demo admin operators and platform settings (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset-passwords",
            action="store_true",
            help=(
                "Overwrite passwords of existing seed admins back to the "
                "demo defaults. Use only when you've lost access in dev."
            ),
        )

    def handle(self, *args, **opts):
        reset = opts.get("reset_passwords", False)

        created, updated, skipped = 0, 0, 0
        for entry in SEED_ADMINS:
            email = entry["email"].lower()
            existing = Admin.objects.filter(email=email).first()
            if existing is None:
                admin = Admin(
                    email=email,
                    name=entry["name"],
                    role=entry["role"],
                )
                admin.set_password(entry["password"])
                admin.save()
                created += 1
                self.stdout.write(
                    self.style.SUCCESS(f"  + created admin {email}")
                )
                continue

            if reset:
                existing.set_password(entry["password"])
                existing.name = entry["name"]
                existing.role = entry["role"]
                existing.save(
                    update_fields=["password_hash", "name", "role"]
                )
                updated += 1
                self.stdout.write(
                    self.style.WARNING(f"  ~ reset password for {email}")
                )
            else:
                skipped += 1
                self.stdout.write(
                    f"  · admin {email} already exists — skipping"
                )

        AppSettings.singleton()
        self.stdout.write(
            self.style.SUCCESS(
                f"Done. created={created} updated={updated} skipped={skipped}"
            )
        )
