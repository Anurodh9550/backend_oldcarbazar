"""GST (tax) helpers shared by subscriptions and listing boosts.

Single source of truth for:
  • the seller's own GST registration (shown on every tax invoice),
  • the 18% GST rate applied on top of the plan/package price, and
  • a light validator for the *customer's* optional GSTIN.

Money is kept in whole rupees everywhere in this project, so GST is
rounded to the nearest rupee. Example: a ₹99 plan → ₹18 GST → ₹117 total.
The seller details can be overridden from the environment without a code
change if the business registration ever updates.
"""
import re

from django.conf import settings

# GST rate applied to the taxable value (base price). 18% for our category.
GST_RATE_PERCENT = int(getattr(settings, "GST_RATE_PERCENT", 18) or 18)

# Seller's own registration — printed on the tax invoice. Defaults to the
# business GSTIN but can be overridden via the GST_SELLER_GSTIN env var.
SELLER_GSTIN = (
    getattr(settings, "GST_SELLER_GSTIN", "") or "09BUUPK1450R1ZQ"
).strip().upper()
SELLER_LEGAL_NAME = getattr(settings, "GST_SELLER_NAME", "") or "Old Car Bazar"

# Standard GSTIN shape: 2-digit state code + 10-char PAN + entity + 'Z' + checksum.
GSTIN_RE = re.compile(
    r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
)


def compute_gst(base_inr: int) -> tuple[int, int, int]:
    """Return (base, gst, total) in whole rupees for a taxable value.

    GST is rounded to the nearest rupee so the three numbers always add up
    and we never charge fractional paise.
    """
    base = int(base_inr or 0)
    gst = round(base * GST_RATE_PERCENT / 100)
    return base, gst, base + gst


def normalize_gstin(value: str | None) -> str:
    """Trim + uppercase a customer-supplied GSTIN (blank stays blank)."""
    return (value or "").strip().upper()


def is_valid_gstin(value: str) -> bool:
    """True for a structurally valid 15-char GSTIN."""
    return bool(GSTIN_RE.match(normalize_gstin(value)))


def seller_invoice_block() -> dict:
    """Seller identity block for invoice payloads."""
    return {
        "name": SELLER_LEGAL_NAME,
        "address": "Old Car Bazar, India",
        "email": "support@oldcarbazar.com",
        "website": "https://oldcarbazar.com",
        "gstin": SELLER_GSTIN,
    }


__all__ = [
    "GST_RATE_PERCENT",
    "SELLER_GSTIN",
    "SELLER_LEGAL_NAME",
    "compute_gst",
    "normalize_gstin",
    "is_valid_gstin",
    "seller_invoice_block",
]
