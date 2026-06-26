"""Seller response-time score for trust badges on listings."""
from __future__ import annotations

from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F
from django.db.models.functions import Extract

from apps.inquiries.models import Inquiry


def recalculate_seller_response_stats(user) -> None:
    """Update cached response tier from responded inquiries."""
    if user is None:
        return

    qs = Inquiry.objects.filter(
        seller=user,
        status=Inquiry.Status.RESPONDED,
        responded_at__isnull=False,
    )
    agg = qs.annotate(
        delta=ExpressionWrapper(
            F("responded_at") - F("created_at"),
            output_field=DurationField(),
        )
    ).aggregate(
        avg_seconds=Avg(Extract("delta", "epoch")),
        total=Count("id"),
    )
    avg_seconds = agg["avg_seconds"]
    total = agg["total"] or 0
    avg_hours = (avg_seconds / 3600.0) if avg_seconds is not None else None

    if total == 0:
        tier = "new"
        avg_hours = None
    elif avg_hours is None:
        tier = "new"
    elif avg_hours <= 2:
        tier = "fast"
    elif avg_hours <= 12:
        tier = "good"
    else:
        tier = "slow"

    user.seller_avg_response_hours = avg_hours
    user.seller_response_tier = tier
    user.save(update_fields=["seller_avg_response_hours", "seller_response_tier", "updated_at"])


def mark_inquiry_responded(inquiry: Inquiry) -> None:
    """Set responded timestamp and refresh seller stats."""
    from django.utils import timezone

    if inquiry.status != Inquiry.Status.RESPONDED:
        inquiry.status = Inquiry.Status.RESPONDED
    if not inquiry.responded_at:
        inquiry.responded_at = timezone.now()
    inquiry.save(update_fields=["status", "responded_at", "updated_at"])
    if inquiry.seller_id:
        recalculate_seller_response_stats(inquiry.seller)
