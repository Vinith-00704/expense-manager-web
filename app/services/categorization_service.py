"""
app/services/categorization_service.py
========================================
Rule-based auto-categorization engine.

Architecture is intentionally designed so the keyword-matching logic
can be swapped for an ML model without changing any callers — callers
always call categorize() and receive (category, confidence_score).
"""
import difflib
from typing import Tuple

# ---------------------------------------------------------------------------
# Category keyword dictionary
# Keys   = category name (must match CATEGORIES in expense.py)
# Values = list of lowercase keywords/phrases matched against merchant name
# ---------------------------------------------------------------------------
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Food & Dining": [
        "swiggy", "zomato", "blinkit", "dunzo", "zepto",
        "restaurant", "cafe", "hotel", "mess", "dhaba", "biryani",
        "pizza", "burger", "mcdonald", "kfc", "dominos", "subway",
        "starbucks", "food", "bakery", "sweet", "juice", "tea",
    ],
    "Transportation": [
        "uber", "ola", "rapido", "metro", "bus", "auto", "cab",
        "taxi", "petrol", "fuel", "irctc", "railway", "train",
        "flight", "air india", "indigo", "spicejet", "parking",
        "toll", "fastag",
    ],
    "Shopping": [
        "amazon", "flipkart", "myntra", "meesho", "nykaa", "ajio",
        "snapdeal", "jiomart", "dmart", "reliance", "big bazaar",
        "shopping", "mall", "mart", "supermarket", "grocery",
        "zepto", "blinkit", "instamart",
    ],
    "Bills & Utilities": [
        "electricity", "bescom", "bwssb", "water", "gas", "broadband",
        "internet", "wifi", "cable", "jio", "airtel", "bsnl", "vi",
        "vodafone", "recharge", "bill", "utility",
    ],
    "Healthcare": [
        "pharmacy", "medical", "hospital", "clinic", "doctor",
        "apollo", "medplus", "netmeds", "1mg", "pharmeasy",
        "health", "lab", "diagnostic", "chemist",
    ],
    "Entertainment": [
        "netflix", "spotify", "hotstar", "disney", "youtube",
        "prime video", "zee5", "sonyliv", "bookmyshow", "pvr",
        "inox", "movie", "concert", "event", "gaming", "steam",
    ],
    "Education": [
        "coursera", "udemy", "byju", "unacademy", "vedantu",
        "school", "college", "university", "tuition", "books",
        "stationery", "exam", "coaching",
    ],
    "Travel": [
        "irctc", "makemytrip", "goibibo", "yatra", "airbnb",
        "oyo", "hotel", "resort", "flight", "holiday", "tour",
        "travel", "booking.com",
    ],
    "Investments": [
        "zerodha", "groww", "coin", "mutual fund", "sip", "stock",
        "equity", "trading", "nse", "bse", "sebi", "lic",
        "insurance", "ppf", "nps",
    ],
    "Salary": [
        "salary", "payroll", "stipend", "wages", "neft salary",
        "monthly pay",
    ],
    "Home & Rent": [
        "rent", "landlord", "maintenance", "society", "nobroker",
        "housing", "apartment", "flat", "pg", "hostel",
    ],
    "Personal Care": [
        "salon", "spa", "barber", "grooming", "parlour", "gym",
        "fitness", "yoga", "cult.fit", "skinceuticals",
    ],
}

# All category names for fuzzy fallback
_ALL_CATEGORIES = list(CATEGORY_KEYWORDS.keys())

# Pre-flatten for fast keyword scanning: {keyword: category}
_KEYWORD_INDEX: dict[str, str] = {}
for _cat, _kws in CATEGORY_KEYWORDS.items():
    for _kw in _kws:
        _KEYWORD_INDEX[_kw] = _cat


def categorize(
    normalized_merchant: str,
    amount: float = 0.0,
    direction: str = "debit",
) -> Tuple[str, float]:
    """
    Determine the most likely expense category for a transaction.

    Args:
        normalized_merchant: Canonical merchant name from MerchantNormalizer.
        amount:              Transaction amount (reserved for future ML use).
        direction:           "debit" or "credit".

    Returns:
        Tuple of (category_name, confidence_score 0.0–1.0).

    Pipeline:
        1. Income shortcut — credit direction defaults to "Salary"
        2. Exact keyword match in merchant name → confidence 0.95
        3. Fuzzy match against category list → confidence 0.60
        4. Fallback → "Other", confidence 0.0
    """
    if not normalized_merchant:
        return ("Other", 0.0)

    lower = normalized_merchant.lower()

    # 1. Credit shortcut
    if direction == "credit":
        # Check if it looks like salary; otherwise treat as Other income
        for kw in CATEGORY_KEYWORDS.get("Salary", []):
            if kw in lower:
                return ("Salary", 0.90)
        return ("Other", 0.50)

    # 2. Exact keyword scan
    for keyword, category in _KEYWORD_INDEX.items():
        if keyword in lower:
            return (category, 0.95)

    # 3. Fuzzy match — compare merchant words against keyword list
    words = lower.split()
    best_cat = None
    best_score = 0.0
    for word in words:
        matches = difflib.get_close_matches(word, _KEYWORD_INDEX.keys(), n=1, cutoff=0.82)
        if matches:
            candidate_cat = _KEYWORD_INDEX[matches[0]]
            score = difflib.SequenceMatcher(None, word, matches[0]).ratio()
            if score > best_score:
                best_score = score
                best_cat = candidate_cat

    if best_cat and best_score >= 0.82:
        return (best_cat, round(best_score * 0.7, 2))  # downgrade confidence

    return ("Other", 0.0)


def categorize_batch(
    transactions: list[dict],
) -> list[dict]:
    """
    Categorize a list of transaction dicts in place.
    Each dict must have 'normalized_merchant', optionally 'amount', 'direction'.
    Adds 'category' and 'confidence_score' keys.
    """
    for tx in transactions:
        cat, conf = categorize(
            tx.get("normalized_merchant", ""),
            tx.get("amount", 0.0),
            tx.get("transaction_direction", "debit"),
        )
        tx["category"] = cat
        tx["confidence_score"] = conf
    return transactions
