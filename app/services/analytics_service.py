from datetime import date
from typing import List
import pandas as pd
from dateutil.relativedelta import relativedelta

from ..models.expense import Expense
from ..models.user import User


def get_cashflow_history(user_id: int, months: int = 12) -> List[dict]:
    salary = float(User.query.get(user_id).monthly_salary or 0)
    from_date = date.today().replace(day=1) - relativedelta(months=months - 1)
    rows = Expense.query.filter(
        Expense.user_id == user_id,
        Expense.expense_date >= from_date,
    ).all()

    result = []
    for i in range(months - 1, -1, -1):
        d = date.today().replace(day=1) - relativedelta(months=i)
        label = d.strftime("%Y-%m")
        display = d.strftime("%b %Y")
        month_rows = [r for r in rows if r.expense_date.strftime("%Y-%m") == label]
        inc = salary + sum(float(r.amount) for r in month_rows if r.entry_type == "income")
        exp = sum(float(r.amount) for r in month_rows if r.entry_type == "expense")
        result.append({"month": display, "income": round(inc, 2), "expense": round(exp, 2), "savings": round(inc - exp, 2)})
    return result


def get_category_breakdown(user_id: int, months: int = 3) -> List[dict]:
    from_date = date.today().replace(day=1) - relativedelta(months=months - 1)
    rows = Expense.query.filter(
        Expense.user_id == user_id,
        Expense.expense_date >= from_date,
        Expense.entry_type == "expense",
    ).all()
    if not rows:
        return []
    df = pd.DataFrame([{"category": r.category, "amount": float(r.amount)} for r in rows])
    grouped = df.groupby("category")["amount"].sum().reset_index().sort_values("amount", ascending=False)
    return [{"category": row["category"], "amount": round(row["amount"], 2)} for _, row in grouped.iterrows()]


def get_health_score(user_id: int) -> dict:
    history = get_cashflow_history(user_id, months=3)
    if not history:
        return {"score": 0, "status": "No Data", "details": []}

    scores = []
    details = []
    for month in history:
        inc = month["income"]
        exp = month["expense"]
        sav = month["savings"]
        pct = (sav / inc * 100) if inc > 0 else 0

        if pct >= 20:
            scores.append(100)
        elif pct >= 10:
            scores.append(70)
        elif pct >= 0:
            scores.append(40)
        else:
            scores.append(0)

        details.append({"month": month["month"], "savings_pct": round(pct, 1)})

    avg_score = round(sum(scores) / len(scores))
    if avg_score >= 80:
        status = "Excellent"
    elif avg_score >= 60:
        status = "Good"
    elif avg_score >= 40:
        status = "Fair"
    else:
        status = "At Risk"

    return {"score": avg_score, "status": status, "details": details}
