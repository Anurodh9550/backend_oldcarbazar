"""Paid listing-boost packages.

A "boost" temporarily lifts a single listing toward the top of the public
feed (just below admin-pinned `featured` cars). Packages live in code so a
price/duration tweak ships with a normal deploy — no DB row to edit.
"""
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class BoostPackage:
    code: str           # stable id stored on the boost order
    name: str           # marketing label
    price_inr: int      # full rupees (₹49 → 49)
    duration_days: int  # how long the boost stays active
    perks: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


BOOST_7 = BoostPackage(
    code="boost_7",
    name="Boost · 7 days",
    price_inr=49,
    duration_days=7,
    perks=[
        "Top placement for 7 days",
        "Highlighted with a Boosted badge",
        "More views & inquiries",
    ],
)

BOOST_15 = BoostPackage(
    code="boost_15",
    name="Boost · 15 days",
    price_inr=99,
    duration_days=15,
    perks=[
        "Top placement for 15 days",
        "Highlighted with a Boosted badge",
        "More views & inquiries",
    ],
)

BOOST_30 = BoostPackage(
    code="boost_30",
    name="Boost · 30 days",
    price_inr=199,
    duration_days=30,
    perks=[
        "Top placement for 30 days",
        "Highlighted with a Boosted badge",
        "Best value for fast selling",
    ],
)

BOOST_PACKAGES: dict[str, BoostPackage] = {
    BOOST_7.code: BOOST_7,
    BOOST_15.code: BOOST_15,
    BOOST_30.code: BOOST_30,
}


def get_boost_package(code: str) -> BoostPackage | None:
    return BOOST_PACKAGES.get(code)
