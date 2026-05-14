"""
app/utils/parsers/csv_parser.py
Generic CSV bank statement parser.

Auto-detects common column naming conventions used by Indian banks.
Returns a normalised list of transaction dicts.
"""
import io
from datetime import datetime, date
from decimal import Decimal, InvalidOperation

import pandas as pd


# Column aliases — expanded to cover all major Indian bank formats
_DATE_ALIASES = {
    "date", "txn date", "transaction date", "value date", "posted date",
    "trans date", "tran date", "booking date", "entry date", "effective date",
    "transaction dt", "txn dt", "dt", "trans dt", "posting date",
}
_DESC_ALIASES = {
    "description", "narration", "particulars", "remarks", "details",
    "merchant", "transaction details", "transaction description",
    "transaction narration", "tran particulars", "transaction remarks",
    "beneficiary", "payee", "cheque details", "narrative",
    "transaction particular", "trans particulars", "trans description",
}
_DEBIT_ALIASES = {
    "debit", "debit amount", "withdrawal", "withdrawal amount", "dr",
    "debit(inr)", "withdrawal(inr)", "debit amt", "dr amount",
    "paid out", "money out", "debit(rs.)", "withdraw", "debits",
    "debit amount(inr)", "amount debited",
}
_CREDIT_ALIASES = {
    "credit", "credit amount", "deposit", "deposit amount", "cr",
    "credit(inr)", "deposit(inr)", "credit amt", "cr amount",
    "paid in", "money in", "credit(rs.)", "deposits", "credits",
    "credit amount(inr)", "amount credited",
}
_AMOUNT_ALIASES = {
    "amount", "transaction amount", "txn amount", "trans amount",
    "amount(inr)", "amount (inr)", "amount(rs)", "amount(rs.)",
    "net amount", "transaction amt",
}
_REF_ALIASES = {
    "reference", "ref no", "chq/ref number", "utr", "txn id",
    "reference no", "reference number", "cheque no", "cheque number",
    "transaction id", "transaction no", "ref number", "chq no",
    "transaction reference", "utr no", "rrn",
}


def _find_col(columns: list[str], aliases: set[str]) -> str | None:
    """Case-insensitive, partial-match column finder."""
    lower_map = {c.lower().strip(): c for c in columns}
    # Exact match first
    for alias in aliases:
        if alias in lower_map:
            return lower_map[alias]
    # Partial match (alias is a substring of the column name)
    for alias in aliases:
        for col_lower, col_orig in lower_map.items():
            if alias in col_lower:
                return col_orig
    return None


def _parse_amount(val) -> Decimal | None:
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    try:
        cleaned = str(val).replace(",", "").replace("₹", "").replace("Rs.", "").strip()
        if cleaned in ("", "-", "nil", "n/a"):
            return None
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _parse_date(val) -> date | None:
    if pd.isna(val):
        return None
    if isinstance(val, (datetime, date)):
        return val.date() if isinstance(val, datetime) else val
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d-%b-%Y", "%d %b %Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(str(val).strip(), fmt).date()
        except ValueError:
            continue
    return None


class CSVParser:
    """Parses generic CSV bank statements into normalised transaction dicts."""

    def parse(self, file_obj, **kwargs) -> list[dict]:
        """
        Args:
            file_obj: File-like object (bytes or text) containing CSV data.

        Returns:
            List of transaction dicts with keys:
                merchant, amount, direction, date, description, reference
        """
        # Read CSV — try common encodings
        content = file_obj.read()
        if isinstance(content, bytes):
            for enc in ("utf-8-sig", "utf-8", "latin-1"):
                try:
                    content = content.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue

        df = pd.read_csv(io.StringIO(content), dtype=str)
        df.columns = df.columns.str.strip()

        cols = list(df.columns)

        date_col   = _find_col(cols, _DATE_ALIASES)
        desc_col   = _find_col(cols, _DESC_ALIASES)
        debit_col  = _find_col(cols, _DEBIT_ALIASES)
        credit_col = _find_col(cols, _CREDIT_ALIASES)
        amt_col    = _find_col(cols, _AMOUNT_ALIASES)
        ref_col    = _find_col(cols, _REF_ALIASES)

        results = []
        for _, row in df.iterrows():
            parsed_date = _parse_date(row.get(date_col)) if date_col else None
            if parsed_date is None:
                continue  # skip rows without a parseable date

            desc = str(row.get(desc_col, "")).strip() if desc_col else ""
            ref  = str(row.get(ref_col,  "")).strip() if ref_col  else ""

            # Determine amount and direction
            direction = "debit"
            amount    = None

            if debit_col and credit_col:
                debit  = _parse_amount(row.get(debit_col))
                credit = _parse_amount(row.get(credit_col))
                if debit and debit > 0:
                    amount, direction = debit, "debit"
                elif credit and credit > 0:
                    amount, direction = credit, "credit"
            elif amt_col:
                amount = _parse_amount(row.get(amt_col))
                if amount and amount < 0:
                    amount, direction = abs(amount), "debit"
                else:
                    direction = "credit" if amount else "debit"

            if amount is None or amount <= 0:
                continue

            results.append({
                "merchant":    desc,
                "description": desc,
                "amount":      float(amount),
                "direction":   direction,
                "date":        parsed_date,
                "reference":   ref,
            })

        return results
