"""
app/services/budget_service.py
CRUD and spend-vs-limit calculations for monthly budgets.
"""
from datetime import date
from decimal import Decimal

from sqlalchemy import func

from ..extensions import db
from ..models.budget import Budget
from ..models.expense import Expense


def _current_month() -> str:
    return date.today().strftime("%Y-%m")


def set_budget(user_id: int, category: str, monthly_limit: float, month: str | None = None) -> Budget:
    """Create or update a budget for the given category+month."""
    month = month or _current_month()
    budget = Budget.query.filter_by(user_id=user_id, category=category, month=month).first()
    if budget:
        budget.monthly_limit = Decimal(str(monthly_limit))
    else:
        budget = Budget(
            user_id=user_id,
            category=category,
            monthly_limit=Decimal(str(monthly_limit)),
            month=month,
        )
        db.session.add(budget)
    db.session.commit()
    return budget


def get_monthly_status(user_id: int, month: str | None = None) -> list[dict]:
    """
    Return each budget for the month with actual spend and % used.
    """
    month = month or _current_month()
    year, mon = map(int, month.split("-"))

    budgets = Budget.query.filter_by(user_id=user_id, month=month).all()

    # Aggregate actual spending per category for the month
    from_date = date(year, mon, 1)
    if mon == 12:
        import calendar
        to_date = date(year, mon, calendar.monthrange(year, mon)[1])
    else:
        to_date = date(year, mon + 1, 1).__class__(year, mon + 1, 1)
        # just get end of month
        import calendar
        to_date = date(year, mon, calendar.monthrange(year, mon)[1])

    spent_rows = db.session.query(
        Expense.category,
        func.sum(Expense.amount).label("total"),
    ).filter(
        Expense.user_id == user_id,
        Expense.entry_type == "expense",
        Expense.expense_date >= from_date,
        Expense.expense_date <= to_date,
    ).group_by(Expense.category).all()

    spent_map = {r.category: float(r.total) for r in spent_rows}

    result = []
    for b in budgets:
        spent  = spent_map.get(b.category, 0.0)
        limit  = float(b.monthly_limit)
        pct    = round((spent / limit * 100) if limit > 0 else 0, 1)
        result.append({
            **b.to_dict(),
            "spent":    round(spent, 2),
            "remaining": round(limit - spent, 2),
            "pct_used":  pct,
            "overspent": spent > limit,
        })

    return result


def list_budgets(user_id: int, month: str | None = None) -> list[dict]:
    month = month or _current_month()
    budgets = Budget.query.filter_by(user_id=user_id, month=month).all()
    return [b.to_dict() for b in budgets]


def delete_budget(budget_id: int, user_id: int) -> bool:
    b = Budget.query.filter_by(id=budget_id, user_id=user_id).first()
    if not b:
        return False
    db.session.delete(b)
    db.session.commit()
    return True
