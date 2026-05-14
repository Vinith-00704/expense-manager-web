"""tests/test_categorization.py"""
import pytest
from app.services.categorization_service import categorize


@pytest.mark.parametrize("merchant,direction,expected_cat", [
    ("Swiggy",      "debit",  "Food & Dining"),
    ("Uber",        "debit",  "Transportation"),
    ("Amazon",      "debit",  "Shopping"),
    ("Netflix",     "debit",  "Entertainment"),
    ("Airtel",      "debit",  "Bills & Utilities"),
    ("Apollo",      "debit",  "Healthcare"),
    ("Salary NEFT", "credit", "Salary"),
    ("Unknown XYZ", "debit",  "Other"),
])
def test_categorize_known_merchants(merchant, direction, expected_cat):
    cat, conf = categorize(merchant, 100.0, direction)
    assert cat == expected_cat, f"Expected {expected_cat} for '{merchant}', got {cat}"


def test_confidence_score_range():
    """Confidence must be between 0.0 and 1.0."""
    _, conf = categorize("Swiggy", 250.0, "debit")
    assert 0.0 <= conf <= 1.0


def test_empty_merchant_returns_other():
    cat, conf = categorize("", 100.0, "debit")
    assert cat == "Other"
    assert conf == 0.0


def test_credit_direction_shortcut():
    cat, _ = categorize("Google Pay", 50000.0, "credit")
    # Credits that are not salary-like should be Other (income)
    assert cat in ("Other", "Salary")
