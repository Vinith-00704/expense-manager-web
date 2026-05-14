"""
app/utils/parsers/banks/sbi_parser.py
SBI Bank statement PDF parser.

SBI account statements column layout:
Txn Date | Value Date | Description | Ref No/Cheque No | Debit | Credit | Balance
"""
import io
from datetime import datetime


def _parse_date(s: str):
    for fmt in ("%d %b %Y", "%d/%m/%Y", "%d-%m-%Y"):
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


class SBIParser:
    """Parser for SBI Bank PDF statements."""

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
                        parsed_date = _parse_date(str(row[0] or ""))
                        if not parsed_date:
                            continue

                        desc  = str(row[2] or "").strip()
                        ref   = str(row[3] or "").strip()
                        debit = _to_float(str(row[4] or ""))
                        credit = _to_float(str(row[5] or ""))

                        if debit and debit > 0:
                            results.append({
                                "merchant": desc, "description": desc,
                                "amount": debit, "direction": "debit",
                                "date": parsed_date, "reference": ref,
                            })
                        elif credit and credit > 0:
                            results.append({
                                "merchant": desc, "description": desc,
                                "amount": credit, "direction": "credit",
                                "date": parsed_date, "reference": ref,
                            })

        return results
