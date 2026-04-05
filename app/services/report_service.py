import io
from typing import Literal
import pandas as pd

from ..models.expense import Expense
from ..models.subscription import Subscription
from ..services import analytics_service


def _to_bytes(df: pd.DataFrame, fmt: str) -> tuple:
    buf = io.BytesIO()
    if fmt == "xlsx":
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ext = "xlsx"
    else:
        df.to_csv(buf, index=False)
        mime = "text/csv"
        ext = "csv"
    buf.seek(0)
    return buf, mime, ext


def expense_report(user_id: int, fmt: str = "csv"):
    rows = Expense.query.filter_by(user_id=user_id).order_by(Expense.expense_date).all()
    df = pd.DataFrame([{
        "Date": r.expense_date, "Type": r.entry_type, "Category": r.category,
        "Description": r.description, "Amount": float(r.amount),
        "Payment Mode": r.payment_mode, "Notes": r.notes,
    } for r in rows])
    return _to_bytes(df, fmt)


def subscription_report(user_id: int, fmt: str = "csv"):
    rows = Subscription.query.filter_by(user_id=user_id).all()
    df = pd.DataFrame([{
        "Name": r.name, "Amount": float(r.amount),
        "Billing Cycle": r.billing_cycle,
        "Last Paid": r.last_paid_date, "Category": r.category,
        "Active": r.is_active,
    } for r in rows])
    return _to_bytes(df, fmt)


def cashflow_report(user_id: int, fmt: str = "csv"):
    history = analytics_service.get_cashflow_history(user_id, months=12)
    df = pd.DataFrame(history)
    return _to_bytes(df, fmt)
