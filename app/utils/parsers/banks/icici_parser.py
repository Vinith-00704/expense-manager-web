"""
app/utils/parsers/banks/icici_parser.py
ICICI Bank statement PDF parser.

ICICI statement columns:
S No. | Transaction Date | Value Date | Description | Remarks | Withdrawal Amount (INR) | Deposit Amount (INR) | Balance (INR)
"""
import io
from datetime import datetime


def _parse_date(s: str):
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d %b %Y"):
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


class ICICIParser:
    """Parser for ICICI Bank PDF statements."""

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
                        if not row or len(row) < 7:
                            continue
                        # Column index 1 = Transaction Date
                        parsed_date = _parse_date(str(row[1] or ""))
                        if not parsed_date:
                            continue

                        desc       = str(row[3] or "").strip()
                        remarks    = str(row[4] or "").strip()
                        withdrawal = _to_float(str(row[5] or ""))
                        deposit    = _to_float(str(row[6] or ""))
                        narration  = f"{desc} {remarks}".strip()

                        if withdrawal and withdrawal > 0:
                            results.append({
                                "merchant": narration, "description": narration,
                                "amount": withdrawal, "direction": "debit",
                                "date": parsed_date, "reference": "",
                            })
                        elif deposit and deposit > 0:
                            results.append({
                                "merchant": narration, "description": narration,
                                "amount": deposit, "direction": "credit",
                                "date": parsed_date, "reference": "",
                            })

        return results
