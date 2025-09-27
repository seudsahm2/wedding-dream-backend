"""Shared constants for the users app (keeps backend+frontend aligned).

If you expand supported provider countries, update ALLOWED_PROVIDER_COUNTRIES
and ensure the frontend `DIAL_CODE_MAP` contains matching dial codes. Consider
later exposing this list via an endpoint if dynamic sync is required.
"""
from __future__ import annotations

# ISO 3166-1 alpha-2 codes for currently supported provider onboarding.
ALLOWED_PROVIDER_COUNTRIES = {
    "ET",  # Ethiopia
    "AE",  # United Arab Emirates
    "SA",  # Saudi Arabia
    "US",  # United States
    "QA",  # Qatar
    "GB",  # United Kingdom
    "FR",  # France
    "DE",  # Germany
    "ES",  # Spain
}

# Dial code mapping (must stay in sync with frontend src/lib/dialCodes.ts)
DIAL_CODE_MAP = {
    "ET": "+251",
    "AE": "+971",
    "SA": "+966",
    "US": "+1",
    "QA": "+974",
    "GB": "+44",
    "FR": "+33",
    "DE": "+49",
    "ES": "+34",
}
