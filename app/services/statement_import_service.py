"""
app/services/statement_import_service.py
==========================================
Orchestrates the full import pipeline:

    upload -> validate -> parse -> normalise -> categorise
    -> deduplicate -> save as pending -> return summary

Also handles the pending workflow:
    confirm_transactions() -> creates Expense records
    reject_transactions()  -> marks rows rejected
"""
import os
import json
from datetime import date
from decimal import Decimal

from ..extensions import db
from ..models.expense import Expense
from ..models.import_history import ImportHistory
from ..models.imported_transaction import ImportedTransaction
from ..services.merchant_normalizer_service import normalize as norm_merchant
from ..services.categorization_service import categorize
from ..services.deduplication_service import compute_hash, check_duplicate
from ..utils.audit import log_action

# Allowed file extensions
ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls", "pdf"}
MAX_FILE_SIZE_MB   = 10


# ── Validation ─────────────────────────────────────────────────────────────

def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _file_type(filename: str) -> str:
    return filename.rsplit(".", 1)[1].lower()


# ── Main import pipeline ───────────────────────────────────────────────────

def process_upload(file_obj, filename: str, user_id: int) -> dict:
    """
    Full pipeline: receive uploaded file → parse → normalise → save pending rows.

    Args:
        file_obj: werkzeug FileStorage (or any file-like with .read()).
        filename: Original filename used to detect file type.
        user_id:  Authenticated user.

    Returns:
        Summary dict with batch_id, counts, and any errors.
    """
    if not _allowed_file(filename):
        raise ValueError(f"Unsupported file type. Allowed: {ALLOWED_EXTENSIONS}")

    ft = _file_type(filename)

    # Create an ImportHistory row immediately so we have a batch_id
    history = ImportHistory(
        user_id=user_id,
        filename=filename,
        file_type=ft if ft in ("csv", "xlsx", "pdf") else "csv",
    )
    db.session.add(history)
    db.session.flush()  # get history.id without full commit

    errors     = []
    raw_rows   = []
    bank_name  = None

    # ── Parse ──────────────────────────────────────────────────────────────
    try:
        from ..utils.parsers import get_parser, detect_bank

        # For PDFs, read a sample to detect the bank
        if ft == "pdf":
            content = file_obj.read()
            try:
                import pdfplumber, io as _io
                with pdfplumber.open(_io.BytesIO(content)) as pdf:
                    sample = (pdf.pages[0].extract_text() or "")[:2000]
                bank_name = detect_bank(sample)
            except Exception:
                bank_name = None
            import io
            file_obj = io.BytesIO(content)

        parser   = get_parser(ft, bank=bank_name)
        raw_rows = parser.parse(file_obj)
    except Exception as exc:
        history.failed_count = 1
        history.error_summary = json.dumps([str(exc)])
        db.session.commit()
        raise ValueError(f"Parsing failed: {exc}") from exc

    history.imported_count = len(raw_rows)
    history.bank_detected  = bank_name

    # ── Normalise, categorise, deduplicate, save ───────────────────────────
    success_count   = 0
    failed_count    = 0
    duplicate_count = 0
    pending_rows    = []

    for row in raw_rows:
        try:
            raw_merchant = row.get("merchant", "") or row.get("description", "")
            norm         = norm_merchant(raw_merchant)
            tx_date      = row.get("date")
            if not tx_date:
                failed_count += 1
                continue

            amount    = float(row.get("amount", 0))
            direction = row.get("direction", "debit")

            if amount <= 0:
                failed_count += 1
                continue

            category, confidence = categorize(norm, amount, direction)

            tx_hash = compute_hash(user_id, norm, amount, tx_date)
            dup     = check_duplicate(user_id, tx_hash, amount, tx_date)

            if dup["is_duplicate"]:
                duplicate_count += 1
                # Still save as duplicate so user can see it
                status = "duplicate"
            else:
                status = "pending"

            pending_rows.append(ImportedTransaction(
                user_id              = user_id,
                source_type          = "statement",
                import_batch_id      = history.id,
                raw_text             = row.get("description", ""),
                merchant             = raw_merchant,
                normalized_merchant  = norm,
                amount               = Decimal(str(amount)),
                transaction_direction = direction,
                transaction_date     = tx_date,
                category             = category,
                payment_method       = "Other",
                description          = row.get("description", ""),
                confidence_score     = confidence,
                transaction_hash     = tx_hash,
                status               = status,
            ))
            success_count += 1

        except Exception as exc:
            errors.append(str(exc))
            failed_count += 1

    # Bulk insert
    if pending_rows:
        db.session.bulk_save_objects(pending_rows)

    history.success_count   = success_count
    history.failed_count    = failed_count
    history.duplicate_count = duplicate_count
    if errors:
        history.error_summary = json.dumps(errors[:20])

    db.session.commit()

    log_action(user_id, "import_upload", "import_history", history.id, {
        "filename": filename, "success": success_count,
        "duplicates": duplicate_count, "failed": failed_count,
    })

    return {
        "batch_id":       history.id,
        "filename":       filename,
        "bank_detected":  bank_name,
        "total_parsed":   len(raw_rows),
        "pending_created": success_count,
        "duplicates":     duplicate_count,
        "failed":         failed_count,
        "errors":         errors[:5],
    }


# ── Pending workflow ───────────────────────────────────────────────────────

def get_pending(user_id: int, page: int = 1, per_page: int = 50) -> dict:
    """Return paginated pending transactions for a user."""
    q = ImportedTransaction.query.filter(
        ImportedTransaction.user_id == user_id,
        ImportedTransaction.status.in_(["pending", "duplicate"]),
    ).order_by(ImportedTransaction.transaction_date.desc())

    total  = q.count()
    items  = q.offset((page - 1) * per_page).limit(per_page).all()
    return {
        "items":    [t.to_dict() for t in items],
        "total":    total,
        "page":     page,
        "pages":    (total + per_page - 1) // per_page,
        "per_page": per_page,
    }


def confirm_transactions(ids: list[int], user_id: int, overrides: dict | None = None) -> dict:
    """
    Confirm pending imported transactions → create Expense records.

    Args:
        ids:       List of ImportedTransaction.id values to confirm.
        user_id:   Must match each row's user_id (security check).
        overrides: Optional per-transaction overrides keyed by str(id).
                   e.g. {"42": {"category": "Food & Dining", "amount": 250}}

    Returns:
        Summary with confirmed_count and any failed ids.
    """
    overrides = overrides or {}
    confirmed  = 0
    failed_ids = []
    new_expenses = []

    rows = ImportedTransaction.query.filter(
        ImportedTransaction.id.in_(ids),
        ImportedTransaction.user_id == user_id,
    ).all()

    for tx in rows:
        try:
            ov = overrides.get(str(tx.id), {})
            amount   = Decimal(str(ov.get("amount", tx.amount)))
            category = ov.get("category", tx.category) or "Other"
            desc     = ov.get("description", tx.description or tx.merchant or "")
            pay_mode = ov.get("payment_method", tx.payment_method or "Other")

            entry_type = "income" if tx.transaction_direction == "credit" else "expense"

            exp = Expense(
                user_id             = user_id,
                category            = category,
                description         = desc,
                amount              = amount,
                expense_date        = tx.transaction_date or date.today(),
                payment_mode        = pay_mode,
                notes               = tx.raw_text or "",
                entry_type          = entry_type,
                transaction_source  = tx.source_type,
                external_reference  = tx.merchant,
                import_batch_id     = tx.import_batch_id,
                is_auto_generated   = True,
                transaction_direction = tx.transaction_direction,
                transaction_hash    = tx.transaction_hash,
            )
            db.session.add(exp)
            db.session.flush()

            tx.status               = "confirmed"
            tx.confirmed_expense_id = exp.id
            new_expenses.append(exp.id)
            confirmed += 1

        except Exception as exc:
            failed_ids.append({"id": tx.id, "error": str(exc)})

    db.session.commit()
    log_action(user_id, "import_confirm", "imported_transaction", None, {
        "confirmed": confirmed, "expense_ids": new_expenses,
    })

    return {"confirmed": confirmed, "failed": failed_ids}


def reject_transactions(ids: list[int], user_id: int) -> dict:
    """Mark pending transactions as rejected."""
    updated = ImportedTransaction.query.filter(
        ImportedTransaction.id.in_(ids),
        ImportedTransaction.user_id == user_id,
        ImportedTransaction.status.in_(["pending", "duplicate"]),
    ).update({"status": "rejected"}, synchronize_session=False)

    db.session.commit()
    log_action(user_id, "import_reject", "imported_transaction", None, {"count": updated})
    return {"rejected": updated}


def get_history(user_id: int, page: int = 1, per_page: int = 20) -> dict:
    """Return paginated import history for a user."""
    q = ImportHistory.query.filter_by(user_id=user_id).order_by(
        ImportHistory.created_at.desc()
    )
    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()
    return {
        "items":    [h.to_dict() for h in items],
        "total":    total,
        "page":     page,
        "pages":    (total + per_page - 1) // per_page,
    }
