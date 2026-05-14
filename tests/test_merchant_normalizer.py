"""tests/test_merchant_normalizer.py"""
import pytest
from app.services.merchant_normalizer_service import normalize


@pytest.mark.parametrize("raw,expected", [
    ("SWIGGY",          "Swiggy"),
    ("SWIGGY LIMITED",  "Swiggy"),
    ("UBER TRIP",       "Uber"),
    ("HDFC BANK",       "HDFC Bank"),
    ("amazon.in",       "Amazon"),
    ("   Netflix   ",   "Netflix"),
    ("",                "Unknown"),
    (None,              "Unknown"),
])
def test_normalize(raw, expected):
    assert normalize(raw) == expected


def test_alias_takes_priority():
    """Alias lookup should win over noise stripping."""
    assert normalize("SWIGGY TECHNOLOGIES PVT LTD") == "Swiggy"


def test_title_case_fallback():
    """Unrecognised merchants should be title-cased."""
    result = normalize("RANDOM VENDOR NAME")
    assert result == result.title() or result == "Unknown"
