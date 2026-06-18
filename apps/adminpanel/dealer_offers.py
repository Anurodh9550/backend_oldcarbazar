"""Dealer launch-offer campaign defaults and helpers."""

DEFAULT_DEALER_OFFER_CAMPAIGN = {
    "enabled": True,
    "default_plan_code": "dealer_trial_20",
    "badge": "DEALER OFFER",
    "title": "20 Din Unlimited Listing!",
    "subtitle": "Dealers ke liye special launch offer",
    "description": (
        "Ab 20 din tak jitni chahein utni gadiyan list karein — bilkul free. "
        "Verified dealer badge, direct buyer contact, WhatsApp leads."
    ),
    "cta_label": "Dealer Join Karein",
    "cta_href": "/partner",
    "max_grants": 100,
}


def merge_dealer_offer_campaign(raw: dict | None) -> dict:
    return {**DEFAULT_DEALER_OFFER_CAMPAIGN, **(raw or {})}
