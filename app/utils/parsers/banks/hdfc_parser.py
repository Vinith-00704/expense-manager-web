"""
app/utils/parsers/banks/hdfc_parser.py
HDFC Bank statement PDF parser.

HDFC account statements have consistent table columns:
Date | Narration | Value Dt | Ref No./Cheque No. | Withdrawal Amt | Deposit Amt | Closing Balance
"""
import io
import re
from datetime import datetime


DATE_RE = re.compile(r"\d{2}/\d{2}/\d{4}")


def _parse_date(s: str):
    try:
        return datetime.strptime(s.strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


def _to_float(s: str) -> float | None:
    if not s or not s.strip():
        return None
    try:
        return float(s.replace(",", "").strip())
    except ValueError:
        return None


class HDFCParser:
    """Parser for HDFC Bank PDF statements."""

    # Expected column indices in HDFC table layout
    COL_DATE       = 0
    COL_NARRATION  = 1
    COL_REF        = 3
    COL_WITHDRAWAL = 4
    COL_DEPOSIT    = 5

    def parse(self, file_obj, **kwargs) -> list[dict]:
        try:
            import pdfplumber
        except ImportError:
            raise ImportError("pip install pdfplumber")

        content = file_obj.read()
        results = []

        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if not row or len(row) < 6:
                            continue
                        parsed_date = _parse_date(str(row[self.COL_DATE] or ""))
                        if not parsed_date:
                            continue

                        narration = str(row[self.COL_NARRATION] or "").strip()
                        ref       = str(row[self.COL_REF] or "").strip()
                        withdrawal = _to_float(str(row[self.COL_WITHDRAWAL] or ""))
                        deposit    = _to_float(str(row[self.COL_DEPOSIT] or ""))

                        if withdrawal and withdrawal > 0:
                            results.append({
                                "merchant": narration, "description": narration,
                                "amount": withdrawal, "direction": "debit",
                                "date": parsed_date, "reference": ref,
                            })
                        elif deposit and deposit > 0:
                            results.append({
                                "merchant": narration, "description": narration,
                                "amount": deposit, "direction": "credit",
                                "date": parsed_date, "reference": ref,
                            })

        return results
