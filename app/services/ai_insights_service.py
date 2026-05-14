"""
app/services/ai_insights_service.py
=====================================
AI-ready insights architecture.

Currently returns rule-based insights. Designed so any function can be
replaced with an LLM call (OpenAI, Gemini, etc.) without changing callers.
All public functions return the same structured dict format.
"""
from datetime import date
from dateutil.relativedelta import relativedelta

from ..models.expense import Expense
from ..models.imported_transaction import ImportedTransaction


def generate_spending_summary(user_id: int) -> dict:
    """
    Return a natural-language spending summary for the current month.
    AI-READY: Replace body with LLM call when integrating.
    """
    today      = date.today()
    month_start = today.replace(day=1)

    expenses = Expense.query.filter(
        Expense.user_id == user_id,
        Expense.entry_type == "expense",
        Expense.expense_date >= month_start,
    ).all()

    total   = sum(float(e.amount) for e in expenses)
    by_cat  = {}
    for e in expenses:
        by_cat[e.category] = by_cat.get(e.category, 0) + float(e.amount)

    top_cat = max(by_cat, key=by_cat.get) if by_cat else None
    summary = (
        f"You have spent {total:.0f} this month across {len(expenses)} transactions. "
        f"Your top spending category is {top_cat} ({by_cat.get(top_cat, 0):.0f})."
        if expenses else "No spending recorded this month."
    )

    return {"summary": summary, "total": total, "by_category": by_cat, "source": "rule_based"}


def detect_anomalies(user_id: int) -> list[dict]:
    """
    Detect unusually high transactions vs the user's 3-month average.
    AI-READY: Enhance with ML anomaly detection later.
    """
    today       = date.today()
    three_months_ago = today.replace(day=1) - relativedelta(months=3)

    all_recent = Expense.query.filter(
        Expense.user_id == user_id,
        Expense.entry_type == "expense",
        Expense.expense_date >= three_months_ago,
    ).all()

    if not all_recent:
        return []

    amounts = [float(e.amount) for e in all_recent]
    avg     = sum(amounts) / len(amounts)
    std_dev = (sum((a - avg) ** 2 for a in amounts) / len(amounts)) ** 0.5
    threshold = avg + 2 * std_dev  # 2-sigma rule

    anomalies = [
        {
            "id": e.id,
            "amount": float(e.amount),
            "category": e.category,
            "date": e.expense_date.isoformat(),
            "description": e.description,
            "reason": f"Amount is {float(e.amount) / avg:.1f}x your average transaction.",
        }
        for e in all_recent if float(e.amount) > threshold
    ]
    return anomalies


def detect_subscriptions(user_id: int) -> list[dict]:
    """
    Detect recurring charges (same merchant, similar amount, monthly pattern).
    AI-READY: Can be enhanced with ML pattern detection.
    """
    six_months_ago = date.today().replace(day=1) - relativedelta(months=6)
    expenses = Expense.query.filter(
        Expense.user_id == user_id,
        Expense.entry_type == "expense",
        Expense.expense_date >= six_months_ago,
    ).all()

    # Group by (description, rounded_amount)
    groups: dict[tuple, list] = {}
    for e in expenses:
        key = (e.description or e.category, round(float(e.amount) / 10) * 10)
        groups.setdefault(key, []).append(e)

    # Flag groups appearing 3+ times across different months
    subscriptions = []
    for (desc, amt_band), rows in groups.items():
        months_seen = {e.expense_date.strftime("%Y-%m") for e in rows}
        if len(months_seen) >= 3:
            subscriptions.append({
                "merchant":        desc,
                "approx_amount":   amt_band,
                "occurrences":     len(rows),
                "months_detected": sorted(months_seen),
            })

    return subscriptions


def get_smart_insights(user_id: int) -> list[str]:
    """
    Generate a list of actionable text insights.
    AI-READY: Replace with LLM-generated insights.
    """
    insights = []
    today       = date.today()
    this_month  = today.replace(day=1)
    last_month  = (this_month - relativedelta(months=1))

    def cat_spend(month_start):
        expenses = Expense.query.filter(
            Expense.user_id == user_id,
            Expense.entry_type == "expense",
            Expense.expense_date >= month_start,
            Expense.expense_date < month_start + relativedelta(months=1),
        ).all()
        result = {}
        for e in expenses:
            result[e.category] = result.get(e.category, 0) + float(e.amount)
        return result

    this = cat_spend(this_month)
    last = cat_spend(last_month)

    for cat in this:
        if cat in last and last[cat] > 0:
            change_pct = (this[cat] - last[cat]) / last[cat] * 100
            if change_pct > 20:
                insights.append(
                    f"{cat} expenses increased by {change_pct:.0f}% compared to last month."
                )
            elif change_pct < -20:
                insights.append(
                    f"Great job! {cat} spending dropped by {abs(change_pct):.0f}% this month."
                )

    subs = detect_subscriptions(user_id)
    for s in subs[:3]:
        insights.append(
            f"Looks like {s['merchant']} (~{s['approx_amount']}) is a recurring subscription."
        )

    if not insights:
        insights.append("Keep it up! Your spending looks stable this month.")

    return insights
