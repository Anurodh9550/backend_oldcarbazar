"""Shared subscription helpers — single source of truth for limits."""
from datetime import timedelta
from typing import Optional

from django.utils import timezone

from .models import Subscription
from .plans import FREE_LISTING_LIMIT, FREE_PLAN, Plan, get_plan


def get_active_subscription(user) -> Optional[Subscription]:
    """Latest non-expired Subscription row for the given user, or None."""
    if not user or not user.is_authenticated:
        return None
    return (
        Subscription.objects.filter(
            user=user,
            status=Subscription.Status.ACTIVE,
            expires_at__gt=timezone.now(),
        )
        .order_by("-expires_at")
        .first()
    )


def get_current_plan(user) -> Plan:
    """Plan the user is currently on (paid plan or implicit Free)."""
    sub = get_active_subscription(user)
    if sub:
        plan = get_plan(sub.plan)
        if plan:
            return plan
    return FREE_PLAN


def count_active_listings(user) -> int:
    """Listings that count toward the seller's quota.

    Active + Draft + Pending all consume the quota: a draft is a
    half-built listing the seller intends to publish, and a pending
    listing is awaiting moderation — both should block the 4th create
    on the Free plan. Sold listings are released back to the quota so
    that a seller who has sold a car can immediately re-list another.
    """
    from apps.listings.models import Listing  # local import: avoid app cycle

    return Listing.objects.filter(
        seller=user,
        status__in=(Listing.Status.ACTIVE, Listing.Status.DRAFT),
    ).count()


def can_publish(user) -> tuple[bool, dict]:
    """Return (allowed, info) for the seller's next create attempt.

    `info` is the same shape returned by /subscriptions/status/, so it
    can be sent straight back to the frontend on a 403 to populate the
    upgrade modal without an extra round-trip.
    """
    plan = get_current_plan(user)
    used = count_active_listings(user)
    limit = plan.listing_limit  # None == unlimited
    info = {
        "plan": plan.code,
        "plan_name": plan.name,
        "listings_used": used,
        "listings_limit": limit,
        "is_unlimited": limit is None,
    }
    if limit is None:
        return True, info
    return used < limit, info


def activate_subscription(
    user,
    plan: Plan,
    *,
    provider: str = "manual",
    provider_payment_id: str = "",
    notes: str = "",
) -> Subscription:
    """Create a Subscription row and return it.

    If the user already has an active subscription on the same plan we
    *extend* the existing window from its current `expires_at` rather
    than starting a brand new one. This is the standard renewal flow
    and avoids losing days the user has already paid for.
    """
    now = timezone.now()
    existing = get_active_subscription(user)

    if existing and existing.plan == plan.code:
        existing.expires_at = existing.expires_at + timedelta(
            days=plan.duration_days
        )
        existing.amount_inr += plan.price_inr
        if provider_payment_id:
            existing.provider_payment_id = provider_payment_id
        if notes:
            existing.notes = (existing.notes + "\n" + notes).strip()
        existing.save(update_fields=[
            "expires_at", "amount_inr", "provider_payment_id",
            "notes", "updated_at",
        ])
        return existing

    return Subscription.objects.create(
        user=user,
        plan=plan.code,
        amount_inr=plan.price_inr,
        started_at=now,
        expires_at=now + timedelta(days=plan.duration_days),
        provider=provider,
        provider_payment_id=provider_payment_id,
        notes=notes,
    )


__all__ = [
    "FREE_LISTING_LIMIT",
    "activate_subscription",
    "can_publish",
    "count_active_listings",
    "get_active_subscription",
    "get_current_plan",
]
