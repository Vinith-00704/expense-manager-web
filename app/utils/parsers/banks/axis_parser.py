"""
app/utils/parsers/banks/axis_parser.py
Axis Bank statement PDF parser.

Axis Bank statement columns:
Tran Date | CHQNO | Particulars | DR | CR | BAL
"""
import io
from datetime import datetime


def _parse_date(s: str):
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%d %b %Y", "%d-%b-%y"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _to_float(s: str) -> float | None:
    if not s or not s.strip() or s.strip() in ("-", ""):
        return None
    try:
        return float(s.replace(",", "").strip())
    except ValueError:
        return None


class AXISParser:
    """Parser for Axis Bank PDF statements."""

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
                        if not row or len(row) < 5:
                            continue
                        parsed_date = _parse_date(str(row[0] or ""))
                        if not parsed_date:
                            continue

                        particulars = str(row[2] or "").strip()
                        dr = _to_float(str(row[3] or ""))
                        cr = _to_float(str(row[4] or ""))

                        if dr and dr > 0:
                            results.append({
                                "merchant": particulars, "description": particulars,
                                "amount": dr, "direction": "debit",
                                "date": parsed_date, "reference": str(row[1] or "").strip(),
                            })
                        elif cr and cr > 0:
                            results.append({
                                "merchant": particulars, "description": particulars,
                                "amount": cr, "direction": "credit",
                                "date": parsed_date, "reference": str(row[1] or "").strip(),
                            })

        return results
