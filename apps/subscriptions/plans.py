"""Subscription plan catalogue.

Plans live in code (not the DB) for now so that pricing/limit tweaks ship
with a normal deploy — no admin click required. Move this to a DB table
if we ever need plans editable from the admin panel.
"""
from dataclasses import asdict, dataclass
from typing import Optional

# A user without an active paid subscription can publish at most this many
# concurrent (non-sold) listings. Sold/expired listings do not count.
FREE_LISTING_LIMIT = 3


@dataclass(frozen=True)
class Plan:
    code: str           # stable id stored in Subscription.plan
    name: str           # marketing label
    price_inr: int      # full rupees (₹99 → 99)
    duration_days: int  # how long one charge keeps the plan active
    listing_limit: Optional[int]  # None = unlimited
    perks: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


# Free plan is implicit — it is what every user has when there is no
# active Subscription row. We still describe it so the /plans/ endpoint
# can present it on the pricing page alongside the paid options.
FREE_PLAN = Plan(
    code="free",
    name="Free",
    price_inr=0,
    duration_days=0,
    listing_limit=FREE_LISTING_LIMIT,
    perks=[
        f"Up to {FREE_LISTING_LIMIT} active listings",
        "Direct buyer-seller chat",
        "Standard search placement",
    ],
)

PRO_PLAN = Plan(
    code="pro",
    name="Pro",
    price_inr=99,
    duration_days=30,
    listing_limit=None,
    perks=[
        "Unlimited active listings",
        "Pro badge on every listing",
        "Priority placement in search",
        "Email + WhatsApp lead alerts",
    ],
)

PRO_YEARLY_PLAN = Plan(
    code="pro_yearly",
    name="Pro (Yearly)",
    price_inr=999,
    duration_days=365,
    listing_limit=None,
    perks=[
        "Unlimited active listings",
        "Pro badge on every listing",
        "Priority placement in search",
        "Email + WhatsApp lead alerts",
        "Save ₹189 vs monthly",
    ],
)

PAID_PLANS: dict[str, Plan] = {
    PRO_PLAN.code: PRO_PLAN,
    PRO_YEARLY_PLAN.code: PRO_YEARLY_PLAN,
}

ALL_PLANS: dict[str, Plan] = {
    FREE_PLAN.code: FREE_PLAN,
    **PAID_PLANS,
}


def get_plan(code: str) -> Optional[Plan]:
    return ALL_PLANS.get(code)
