from datetime import datetime, date
from typing import List, Dict
import pandas as pd
from dateutil.relativedelta import relativedelta

from ..models.expense import Expense
from ..models.subscription import Subscription, CYCLE_MONTHS
from ..models.trip import Trip, TravelExpense
from ..models.user import User


def _monthly_salary(user_id: int) -> float:
    user = User.query.get(user_id)
    return float(user.monthly_salary or 0) if user else 0.0


def get_summary(user_id: int) -> dict:
    today = date.today()
    month_start = today.replace(day=1)

    rows = (
        Expense.query.filter(
            Expense.user_id == user_id,
            Expense.expense_date >= month_start,
        ).all()
    )

    income = _monthly_salary(user_id)
    spent = 0.0
    for r in rows:
        if r.entry_type == "income":
            income += float(r.amount)
        else:
            spent += float(r.amount)

    saved = income - spent
    savings_pct = round((saved / income) * 100, 1) if income > 0 else 0

    return {
        "income": round(income, 2),
        "spent": round(spent, 2),
        "saved": round(saved, 2),
        "savings_pct": savings_pct,
        "month": today.strftime("%B %Y"),
    }


def get_savings_history(user_id: int, months: int = 6) -> List[dict]:
    salary = _monthly_salary(user_id)
    from_date = (date.today().replace(day=1) - relativedelta(months=months - 1))

    rows = (
        Expense.query.filter(
            Expense.user_id == user_id,
            Expense.expense_date >= from_date,
        ).all()
    )

    if not rows:
        periods = []
        for i in range(months - 1, -1, -1):
            d = date.today().replace(day=1) - relativedelta(months=i)
            periods.append({"month": d.strftime("%b %Y"), "income": salary, "expense": 0, "savings": salary})
        return periods

    df = pd.DataFrame([
        {"amount": float(r.amount), "entry_type": r.entry_type,
         "month": r.expense_date.strftime("%Y-%m")}
        for r in rows
    ])

    result = []
    for i in range(months - 1, -1, -1):
        d = date.today().replace(day=1) - relativedelta(months=i)
        label = d.strftime("%Y-%m")
        display = d.strftime("%b %Y")
        month_df = df[df["month"] == label] if not df.empty else pd.DataFrame()
        inc = salary + float(month_df[month_df["entry_type"] == "income"]["amount"].sum()) if not month_df.empty else salary
        exp = float(month_df[month_df["entry_type"] == "expense"]["amount"].sum()) if not month_df.empty else 0
        result.append({
            "month": display, "income": round(inc, 2),
            "expense": round(exp, 2), "savings": round(inc - exp, 2),
        })
    return result


def get_upcoming_expenses(user_id: int) -> List[dict]:
    today = date.today()
    upcoming = []

    subs = Subscription.query.filter_by(user_id=user_id, is_active=True).all()
    for s in subs:
        months_add = CYCLE_MONTHS.get(s.billing_cycle, 1)
        next_renewal = s.last_paid_date + relativedelta(months=months_add)
        if next_renewal >= today:
            days_left = (next_renewal - today).days
            upcoming.append({
                "title": s.name, "amount": float(s.amount),
                "due_date": next_renewal.isoformat(), "days_left": days_left,
                "type": "subscription",
            })

    trips = Trip.query.filter(
        Trip.user_id == user_id, Trip.start_date >= today
    ).all()
    for t in trips:
        days_left = (t.start_date - today).days
        upcoming.append({
            "title": f"Trip: {t.destination}", "amount": float(t.total_budget),
            "due_date": t.start_date.isoformat(), "days_left": days_left,
            "type": "trip",
        })

    upcoming.sort(key=lambda x: x["due_date"])
    return upcoming[:8]


def get_alerts(user_id: int) -> List[dict]:
    alerts = []
    summary = get_summary(user_id)

    if summary["income"] > 0:
        if summary["saved"] < 0:
            alerts.append({"type": "overspend", "message": "You spent more than you earned this month", "severity": "danger"})
        elif summary["savings_pct"] < 10:
            alerts.append({"type": "warning", "message": f"Savings are only {summary['savings_pct']}% of income", "severity": "warning"})

    today = date.today()
    subs = Subscription.query.filter_by(user_id=user_id, is_active=True).all()
    for s in subs:
        months_add = CYCLE_MONTHS.get(s.billing_cycle, 1)
        next_renewal = s.last_paid_date + relativedelta(months=months_add)
        days_left = (next_renewal - today).days
        if 0 <= days_left <= 3:
            alerts.append({"type": "subscription", "message": f"{s.name} renews in {days_left} day(s)", "severity": "warning"})

    return alerts


def get_category_breakdown(user_id: int) -> List[dict]:
    today = date.today()
    month_start = today.replace(day=1)
    rows = Expense.query.filter(
        Expense.user_id == user_id,
        Expense.expense_date >= month_start,
        Expense.entry_type == "expense",
    ).all()
    if not rows:
        return []
    df = pd.DataFrame([{"category": r.category, "amount": float(r.amount)} for r in rows])
    grouped = df.groupby("category")["amount"].sum().reset_index()
    grouped = grouped.sort_values("amount", ascending=False)
    return [{"category": row["category"], "amount": round(row["amount"], 2)} for _, row in grouped.iterrows()]
