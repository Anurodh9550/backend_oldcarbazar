"""Seed default admin operators + app settings.

Run automatically on every Render deploy via ``build.sh``. Idempotent — safe
to re-run; only creates the row when an admin with the same email doesn't
exist yet. Existing admins are NOT overwritten so a production password
change is not undone by the next deploy.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.adminpanel.models import Admin, AppSettings


SEED_ADS = [
    {
        "id": "demo-ad-1",
        "enabled": True,
        "name": "Demo — Featured cars",
        "title": "Big Savings on Used Cars",
        "description": "Up to ₹50,000 off on verified cars",
        "imageUrl": "https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&w=1000&q=70",
        "videoUrl": "",
        "ctaLabel": "Browse",
        "ctaHref": "/used-cars",
        "pages": ["home"],
        "placement": "top",
        "style": "image",
        "platform": "both",
    },
    {
        "id": "demo-ad-video",
        "enabled": True,
        "name": "Demo — Video banner",
        "title": "Watch Our Cars in Action",
        "description": "Real footage of inspected cars",
        "imageUrl": "https://images.unsplash.com/photo-1494976388531-d1058494cdd8?auto=format&fit=crop&w=1000&q=70",
        "videoUrl": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerJoyrides.mp4",
        "ctaLabel": "Watch",
        "ctaHref": "/used-cars",
        "pages": ["home"],
        "placement": "top",
        "style": "video",
        "platform": "both",
    },
    {
        "id": "demo-ad-2",
        "enabled": True,
        "name": "Demo — Sell your car",
        "title": "Sell Your Car at Best Price",
        "description": "List free, reach thousands of buyers",
        "imageUrl": "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?auto=format&fit=crop&w=1000&q=70",
        "videoUrl": "",
        "ctaLabel": "Sell Now",
        "ctaHref": "/sell-car",
        "pages": ["home"],
        "placement": "top",
        "style": "image",
        "platform": "both",
    },
    {
        "id": "demo-ad-3",
        "enabled": True,
        "name": "Demo — Assured cars",
        "title": "Old Car Bazar Assured",
        "description": "200-point inspected, warranty included",
        "imageUrl": "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?auto=format&fit=crop&w=1000&q=70",
        "videoUrl": "",
        "ctaLabel": "Explore",
        "ctaHref": "/assured",
        "pages": ["home"],
        "placement": "top",
        "style": "image",
        "platform": "both",
    },
]


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

        settings = AppSettings.singleton()
        if not settings.ads:
            settings.ads = SEED_ADS
            settings.save(update_fields=["ads"])
            self.stdout.write(
                self.style.SUCCESS(f"  + seeded {len(SEED_ADS)} demo ads")
            )
        else:
            self.stdout.write("  · ads already present — skipping ad seed")

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. created={created} updated={updated} skipped={skipped}"
            )
        )
