"""
app/routes/imports.py
Blueprint for /api/imports/* — statement file upload and pending workflow.
"""
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..utils.response import success, error
from ..services import statement_import_service as svc

imports_bp = Blueprint("imports", __name__)


@imports_bp.post("/upload")
@jwt_required()
def upload():
    """POST /api/imports/upload — Multipart form-data with field 'file'."""
    user_id = int(get_jwt_identity())

    if "file" not in request.files:
        return error("No file uploaded.", 400)

    file = request.files["file"]
    if not file.filename:
        return error("Empty filename.", 400)

    try:
        result = svc.process_upload(file, file.filename, user_id)
        return success(result, "Statement processed successfully.")
    except ValueError as exc:
        return error(str(exc), 422)
    except Exception as exc:
        return error(f"Internal error: {exc}", 500)


@imports_bp.get("/pending")
@jwt_required()
def pending():
    """GET /api/imports/pending?page=1&per_page=50"""
    user_id  = int(get_jwt_identity())
    page     = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 50)), 200)
    return success(svc.get_pending(user_id, page, per_page))


@imports_bp.patch("/pending/<int:tx_id>")
@jwt_required()
def edit_pending(tx_id: int):
    """
    PATCH /api/imports/pending/<id>
    Edit a pending transaction before confirming it.

    Accepted fields (all optional):
      category, merchant, amount, transaction_date, notes, payment_method, direction
    """
    user_id = int(get_jwt_identity())
    body    = request.get_json(silent=True) or {}

    from ..models.imported_transaction import ImportedTransaction
    from ..extensions import db
    from decimal import Decimal, InvalidOperation
    from datetime import datetime

    tx = ImportedTransaction.query.filter_by(
        id=tx_id, user_id=user_id
    ).first()
    if not tx:
        return error("Transaction not found.", 404)
    if tx.status not in ("pending", "duplicate"):
        return error("Only pending transactions can be edited.", 400)

    ALLOWED_CATEGORIES = [
        "Food & Dining", "Transportation", "Shopping", "Bills & Utilities",
        "Healthcare", "Entertainment", "Education", "Travel",
        "Investments", "Home & Rent", "Personal Care", "Salary",
        "Freelance", "Business", "Gift", "Other"
    ]

    if "category" in body:
        cat = body["category"].strip()
        if cat not in ALLOWED_CATEGORIES:
            return error(f"Invalid category.", 400)
        tx.category = cat

    if "merchant" in body:
        tx.normalized_merchant = body["merchant"].strip()

    if "amount" in body:
        try:
            amt = Decimal(str(body["amount"]))
            if amt <= 0:
                return error("Amount must be positive.", 400)
            tx.amount = amt
        except InvalidOperation:
            return error("Invalid amount.", 400)

    if "direction" in body:
        d = body["direction"].strip().lower()
        if d not in ("debit", "credit"):
            return error("direction must be 'debit' or 'credit'.", 400)
        tx.transaction_direction = d

    if "transaction_date" in body:
        try:
            tx.transaction_date = datetime.strptime(
                body["transaction_date"], "%Y-%m-%d"
            ).date()
        except ValueError:
            return error("Invalid date. Use YYYY-MM-DD.", 400)

    if "notes" in body:
        tx.notes = body["notes"].strip() if hasattr(tx, "notes") else None

    if "payment_method" in body:
        tx.payment_method = body["payment_method"].strip()

    db.session.commit()
    return success(tx.to_dict(), "Transaction updated.")


@imports_bp.post("/confirm")
@jwt_required()
def confirm():
    """POST /api/imports/confirm — { ids: [...] }"""
    user_id = int(get_jwt_identity())
    body    = request.get_json(silent=True) or {}
    ids     = body.get("ids", [])
    if not ids:
        return error("No transaction IDs provided.", 400)

    result = svc.confirm_transactions(ids, user_id, body.get("overrides"))
    return success(result, f"{result['confirmed']} transaction(s) confirmed.")


@imports_bp.post("/reject")
@jwt_required()
def reject():
    """POST /api/imports/reject — { ids: [...] }"""
    user_id = int(get_jwt_identity())
    body    = request.get_json(silent=True) or {}
    ids     = body.get("ids", [])
    if not ids:
        return error("No transaction IDs provided.", 400)

    result = svc.reject_transactions(ids, user_id)
    return success(result, f"{result['rejected']} transaction(s) rejected.")


@imports_bp.get("/history")
@jwt_required()
def history():
    """GET /api/imports/history?page=1&per_page=20"""
    user_id  = int(get_jwt_identity())
    page     = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 20)), 100)
    return success(svc.get_history(user_id, page, per_page))
