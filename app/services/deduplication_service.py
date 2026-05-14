"""
app/services/deduplication_service.py
=======================================
Prevents duplicate transaction imports using deterministic SHA-256 hashing.

Hash input: user_id + normalized_merchant + rounded_amount + ISO_date
This combination is collision-resistant for real financial transactions.
"""
import hashlib
from datetime import date, timedelta
from decimal import Decimal

from ..models.expense import Expense
from ..models.imported_transaction import ImportedTransaction
from ..extensions import db

# Configurable tolerance window
AMOUNT_TOLERANCE = Decimal("0.50")   # ±₹0.50 — covers rounding differences
DATE_WINDOW_DAYS = 1                 # check ±1 calendar day


def compute_hash(
    user_id: int,
    normalized_merchant: str,
    amount: float | Decimal,
    transaction_date: date,
) -> str:
    """
    Compute a deterministic SHA-256 deduplication hash.

    Args:
        user_id:             Scopes hash to this user (prevents cross-user collisions).
        normalized_merchant: Canonical merchant from MerchantNormalizer.
        amount:              Transaction amount (rounded to 2 dp for stability).
        transaction_date:    Date of the transaction.

    Returns:
        64-character hex digest.
    """
    amount_str = f"{Decimal(str(amount)):.2f}"
    date_str   = transaction_date.isoformat() if hasattr(transaction_date, "isoformat") else str(transaction_date)
    raw        = f"{user_id}|{normalized_merchant.lower().strip()}|{amount_str}|{date_str}"
    return hashlib.sha256(raw.encode()).hexdigest()


def check_duplicate(
    user_id: int,
    tx_hash: str,
    amount: float | Decimal | None = None,
    transaction_date: date | None = None,
) -> dict:
    """
    Check whether this transaction already exists.

    Strategy (in order):
        1. Exact hash match in `expenses` table
        2. Exact hash match in `imported_transactions` table
        3. Fuzzy match: same user, ±1 day, amount within tolerance (optional)

    Args:
        user_id:          Owning user.
        tx_hash:          Pre-computed SHA-256 hash.
        amount:           Used for fuzzy match (optional).
        transaction_date: Used for fuzzy match (optional).

    Returns:
        {
            "is_duplicate": bool,
            "source": "expense" | "imported" | "fuzzy" | None,
            "existing_id": int | None,
        }
    """
    # 1. Exact match in confirmed expenses
    existing_expense = Expense.query.filter_by(
        user_id=user_id, transaction_hash=tx_hash
    ).first()
    if existing_expense:
        return {"is_duplicate": True, "source": "expense", "existing_id": existing_expense.id}

    # 2. Exact match in pending / imported transactions
    existing_import = ImportedTransaction.query.filter(
        ImportedTransaction.user_id == user_id,
        ImportedTransaction.transaction_hash == tx_hash,
        ImportedTransaction.status.in_(["pending", "confirmed"]),
    ).first()
    if existing_import:
        return {"is_duplicate": True, "source": "imported", "existing_id": existing_import.id}

    # 3. Fuzzy fallback — only runs if amount + date provided
    if amount is not None and transaction_date is not None:
        amt = Decimal(str(amount))
        date_lo = transaction_date - timedelta(days=DATE_WINDOW_DAYS)
        date_hi = transaction_date + timedelta(days=DATE_WINDOW_DAYS)

        fuzzy_expense = Expense.query.filter(
            Expense.user_id == user_id,
            Expense.expense_date.between(date_lo, date_hi),
            Expense.amount.between(amt - AMOUNT_TOLERANCE, amt + AMOUNT_TOLERANCE),
        ).first()
        if fuzzy_expense:
            return {"is_duplicate": True, "source": "fuzzy", "existing_id": fuzzy_expense.id}

    return {"is_duplicate": False, "source": None, "existing_id": None}
