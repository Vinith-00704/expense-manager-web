"""
app/services/merchant_normalizer_service.py
============================================
Normalizes raw merchant names before categorization and deduplication.

Called at the top of every import/SMS parsing pipeline to ensure
consistent merchant strings across all analysis engines.
"""
import re
import unicodedata

# Canonical merchant alias map.
# Keys  = regex patterns (case-insensitive) matching raw bank strings.
# Values = the canonical display name to store.
MERCHANT_ALIASES: list[tuple[str, str]] = [
    # Food delivery
    (r"swiggy", "Swiggy"),
    (r"zomato", "Zomato"),
    (r"blinkit|grofers", "Blinkit"),
    (r"dunzo", "Dunzo"),
    (r"zepto", "Zepto"),
    # Rides
    (r"uber", "Uber"),
    (r"ola\b|ola cabs", "Ola"),
    (r"rapido", "Rapido"),
    # E-commerce
    (r"amazon", "Amazon"),
    (r"flipkart", "Flipkart"),
    (r"myntra", "Myntra"),
    (r"meesho", "Meesho"),
    (r"nykaa", "Nykaa"),
    # Streaming
    (r"netflix", "Netflix"),
    (r"spotify", "Spotify"),
    (r"hotstar|disney", "Disney+ Hotstar"),
    (r"youtube premium", "YouTube Premium"),
    (r"amazon prime", "Amazon Prime"),
    # Payments / wallets
    (r"google pay|gpay", "Google Pay"),
    (r"phonepe", "PhonePe"),
    (r"paytm", "Paytm"),
    (r"bhim", "BHIM UPI"),
    # Telecom
    (r"jio|reliance jio", "Jio"),
    (r"airtel", "Airtel"),
    (r"vi\b|vodafone|idea", "Vodafone Idea"),
    (r"bsnl", "BSNL"),
    # Utilities
    (r"bescom|electricity", "Electricity"),
    (r"bwssb|water board", "Water Board"),
    # ATM
    (r"atm withdrawal|cash withdrawal", "ATM Withdrawal"),
    # Banks
    (r"hdfc bank", "HDFC Bank"),
    (r"sbi|state bank", "SBI"),
    (r"icici bank", "ICICI Bank"),
    (r"axis bank", "Axis Bank"),
]

# Compiled once at import time for performance
_COMPILED_ALIASES = [
    (re.compile(pattern, re.IGNORECASE), canonical)
    for pattern, canonical in MERCHANT_ALIASES
]

# Noise tokens commonly appended by banks that add no meaning
_NOISE_SUFFIXES = re.compile(
    r"\b(pvt|ltd|llp|inc|limited|private|bank|india|payments|technologies|"
    r"solutions|services|digital|online|internet|retail|store|shop)\b",
    re.IGNORECASE,
)
_WHITESPACE = re.compile(r"\s+")
_NON_ALPHA  = re.compile(r"[^a-z0-9\s]")


def normalize(raw: str | None) -> str:
    """
    Return a canonical merchant name from a raw bank string.

    Pipeline:
        1. Unicode → ASCII transliteration
        2. Lowercase
        3. Remove special characters
        4. Alias dictionary lookup (returns immediately if matched)
        5. Strip noise suffixes
        6. Title-case result

    Args:
        raw: The merchant string as it appears in the bank statement / SMS.

    Returns:
        Canonical merchant name (e.g. "SWIGGY LIMITED" → "Swiggy").
        Returns "Unknown" if input is empty.
    """
    if not raw or not raw.strip():
        return "Unknown"

    # Step 1 — Unicode normalisation (handles Indian rupee, special chars)
    text = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode()

    # Step 2-3 — lowercase, remove non-alphanumeric (keep spaces)
    text = _NON_ALPHA.sub(" ", text.lower())
    text = _WHITESPACE.sub(" ", text).strip()

    # Step 4 — alias lookup (exact regex match against canonical list)
    for pattern, canonical in _COMPILED_ALIASES:
        if pattern.search(text):
            return canonical

    # Step 5 — strip common banking noise words
    text = _NOISE_SUFFIXES.sub(" ", text)
    text = _WHITESPACE.sub(" ", text).strip()

    # Step 6 — title-case the cleaned string
    return text.title() if text else "Unknown"


def normalize_batch(merchants: list[str]) -> list[str]:
    """Normalize a list of merchant strings."""
    return [normalize(m) for m in merchants]
