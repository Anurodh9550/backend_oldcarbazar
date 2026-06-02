"""Public dealer directory.

A "dealer" is simply any registered seller (user with role
seller / both) who has at least one approved+active listing. We
aggregate per-seller stats from the listings table so the dealers
page can render rich cards without N+1 queries.

Endpoints (mounted at /api/v1/dealers/):
    GET /                    — paginated list of dealers
    GET /<user-uuid>/        — single dealer profile + recent listings
"""
from django.db.models import Count, Max, Min, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.listings.models import Listing
from apps.listings.serializers import ListingSerializer
from apps.subscriptions.models import Subscription
from .models import User


def _public_seller_qs():
    """Approved-active listings whose seller still exists and is allowed."""
    return Listing.objects.filter(
        seller__isnull=False,
        seller__status=User.Status.ACTIVE,
        moderation=Listing.Moderation.APPROVED,
        status=Listing.Status.ACTIVE,
    )


def _dealer_stats_queryset():
    """One row per seller, with aggregate columns the card UI needs."""
    return (
        User.objects.filter(
            role__in=(User.Role.SELLER, User.Role.BOTH),
            status=User.Status.ACTIVE,
            listings__moderation=Listing.Moderation.APPROVED,
            listings__status=Listing.Status.ACTIVE,
        )
        .annotate(
            active_listings_count=Count(
                "listings",
                filter=Q(
                    listings__moderation=Listing.Moderation.APPROVED,
                    listings__status=Listing.Status.ACTIVE,
                ),
                distinct=True,
            ),
            min_price=Min(
                "listings__price_inr",
                filter=Q(
                    listings__moderation=Listing.Moderation.APPROVED,
                    listings__status=Listing.Status.ACTIVE,
                ),
            ),
            max_price=Max(
                "listings__price_inr",
                filter=Q(
                    listings__moderation=Listing.Moderation.APPROVED,
                    listings__status=Listing.Status.ACTIVE,
                ),
            ),
            last_listed_at=Max(
                "listings__created_at",
                filter=Q(
                    listings__moderation=Listing.Moderation.APPROVED,
                    listings__status=Listing.Status.ACTIVE,
                ),
            ),
        )
        .distinct()
    )


def _active_pro_user_ids() -> set[str]:
    """Set of UUIDs of users with a still-active paid subscription."""
    return set(
        Subscription.objects.filter(
            status=Subscription.Status.ACTIVE,
            expires_at__gt=timezone.now(),
        ).values_list("user_id", flat=True)
    )


def _mask_phone(phone: str) -> str:
    """`9876543210` → `98XXXXXX10` — enough for users to recognise their
    own number on their own card but useless for scrapers."""
    if not phone or len(phone) < 4:
        return ""
    return phone[:2] + "X" * (len(phone) - 4) + phone[-2:]


def _dealer_to_card(user: User, *, pro_ids: set[str]) -> dict:
    """Card-sized payload for the dealers list."""
    cities = list(
        _public_seller_qs()
        .filter(seller=user)
        .values_list("location", flat=True)
        .distinct()
    )
    brands = list(
        _public_seller_qs()
        .filter(seller=user)
        .order_by("brand")
        .values_list("brand", flat=True)
        .distinct()[:8]
    )
    return {
        "id": str(user.id),
        "name": user.name,
        "primary_city": user.city or (cities[0] if cities else ""),
        "cities": cities,
        "avatar_url": user.avatar_url,
        "phone": _mask_phone(user.phone),
        "active_listings_count": getattr(user, "active_listings_count", 0),
        "min_price_inr": (
            str(user.min_price) if getattr(user, "min_price", None) is not None else None
        ),
        "max_price_inr": (
            str(user.max_price) if getattr(user, "max_price", None) is not None else None
        ),
        "brands": brands,
        "is_pro": str(user.id) in pro_ids,
        "last_listed_at": getattr(user, "last_listed_at", None),
        "member_since": user.date_joined,
    }


class DealersListView(APIView):
    """Public list of dealers, sorted by `?sort=` (defaults to active count)."""
    permission_classes = (permissions.AllowAny,)
    pagination_class = LimitOffsetPagination

    SORT_MAP = {
        "listings": "-active_listings_count",
        "newest": "-last_listed_at",
        "name": "name",
    }

    def get(self, request):
        qs = _dealer_stats_queryset()

        q = (request.query_params.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(city__icontains=q)
                | Q(listings__location__icontains=q)
            ).distinct()

        city = (request.query_params.get("city") or "").strip()
        if city:
            qs = qs.filter(
                Q(city__iexact=city)
                | Q(listings__location__iexact=city)
            ).distinct()

        sort_key = (request.query_params.get("sort") or "listings").lower()
        qs = qs.order_by(self.SORT_MAP.get(sort_key, self.SORT_MAP["listings"]))

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(qs, request, view=self)
        pro_ids = _active_pro_user_ids()
        page_data = [_dealer_to_card(u, pro_ids=pro_ids) for u in (page or qs)]

        if page is not None:
            return paginator.get_paginated_response(page_data)
        return Response(page_data)


class DealerDetailView(APIView):
    """Single dealer profile plus their recent listings."""
    permission_classes = (permissions.AllowAny,)

    def get(self, request, dealer_id: str):
        user = get_object_or_404(
            _dealer_stats_queryset(),
            id=dealer_id,
        )

        listings_qs = (
            _public_seller_qs()
            .filter(seller=user)
            .prefetch_related("photos")
            .order_by("-created_at")
        )
        recent = listings_qs[:24]

        pro_ids = _active_pro_user_ids()
        card = _dealer_to_card(user, pro_ids=pro_ids)
        # Detail view exposes the real phone — buyers need to be able
        # to actually call the seller from here.
        card["phone"] = user.phone
        card["listings"] = ListingSerializer(recent, many=True).data
        card["total_listings_count"] = listings_qs.count()
        return Response(card)
