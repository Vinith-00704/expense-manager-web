"""tests/test_deduplication.py"""
import pytest
from datetime import date
from app.services.deduplication_service import compute_hash


def test_hash_is_deterministic():
    h1 = compute_hash(1, "Swiggy", 250.0, date(2026, 5, 1))
    h2 = compute_hash(1, "Swiggy", 250.0, date(2026, 5, 1))
    assert h1 == h2


def test_hash_differs_by_user():
    h1 = compute_hash(1, "Swiggy", 250.0, date(2026, 5, 1))
    h2 = compute_hash(2, "Swiggy", 250.0, date(2026, 5, 1))
    assert h1 != h2


def test_hash_differs_by_amount():
    h1 = compute_hash(1, "Swiggy", 250.0, date(2026, 5, 1))
    h2 = compute_hash(1, "Swiggy", 251.0, date(2026, 5, 1))
    assert h1 != h2


def test_hash_is_64_chars():
    h = compute_hash(1, "Uber", 100.0, date(2026, 5, 1))
    assert len(h) == 64


def test_hash_merchant_case_insensitive():
    """Normalised merchants should produce the same hash regardless of case."""
    h1 = compute_hash(1, "swiggy", 100.0, date(2026, 5, 1))
    h2 = compute_hash(1, "SWIGGY", 100.0, date(2026, 5, 1))
    assert h1 == h2
