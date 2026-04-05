from datetime import date


def validate_amount(value) -> float:
    try:
        v = float(value)
        if v <= 0:
            raise ValueError
        return round(v, 2)
    except (TypeError, ValueError):
        raise ValueError("Amount must be a positive number")


def validate_date(value: str) -> date:
    from datetime import datetime
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        raise ValueError("Date must be in YYYY-MM-DD format")


def require_fields(data: dict, *fields):
    missing = [f for f in fields if not data.get(f)]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")
