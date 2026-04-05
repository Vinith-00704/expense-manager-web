from datetime import date, datetime
from typing import List, Optional

from ..extensions import db
from ..models.expense import Expense, CATEGORIES, PAYMENT_MODES


def add_expense(user_id: int, data: dict) -> dict:
    from ..utils.validators import validate_amount, validate_date
    exp = Expense(
        user_id=user_id,
        category=data.get("category", "Other"),
        description=data.get("description", ""),
        amount=validate_amount(data["amount"]),
        expense_date=validate_date(data["expense_date"]),
        payment_mode=data.get("payment_mode", "Cash"),
        notes=data.get("notes", ""),
        entry_type=data.get("entry_type", "expense"),
    )
    db.session.add(exp)
    db.session.commit()
    return exp.to_dict()


def list_expenses(
    user_id: int,
    entry_type: Optional[str] = None,
    category: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 100,
) -> List[dict]:
    q = Expense.query.filter_by(user_id=user_id)
    if entry_type in ("expense", "income"):
        q = q.filter_by(entry_type=entry_type)
    if category:
        q = q.filter_by(category=category)
    if date_from:
        q = q.filter(Expense.expense_date >= date_from)
    if date_to:
        q = q.filter(Expense.expense_date <= date_to)
    rows = q.order_by(Expense.expense_date.desc()).limit(limit).all()
    return [r.to_dict() for r in rows]


def get_expense(user_id: int, expense_id: int) -> Optional[dict]:
    exp = Expense.query.filter_by(id=expense_id, user_id=user_id).first()
    return exp.to_dict() if exp else None


def update_expense(user_id: int, expense_id: int, data: dict) -> dict:
    from ..utils.validators import validate_amount, validate_date
    exp = Expense.query.filter_by(id=expense_id, user_id=user_id).first_or_404()
    if "category" in data:
        exp.category = data["category"]
    if "description" in data:
        exp.description = data["description"]
    if "amount" in data:
        exp.amount = validate_amount(data["amount"])
    if "expense_date" in data:
        exp.expense_date = validate_date(data["expense_date"])
    if "payment_mode" in data:
        exp.payment_mode = data["payment_mode"]
    if "notes" in data:
        exp.notes = data["notes"]
    if "entry_type" in data:
        exp.entry_type = data["entry_type"]
    db.session.commit()
    return exp.to_dict()


def delete_expense(user_id: int, expense_id: int) -> None:
    exp = Expense.query.filter_by(id=expense_id, user_id=user_id).first_or_404()
    db.session.delete(exp)
    db.session.commit()


def get_categories() -> List[str]:
    return CATEGORIES


def get_payment_modes() -> List[str]:
    return PAYMENT_MODES
