"""
app/utils/parsers/pdf_parser.py
Generic PDF statement parser using pdfplumber.
Falls back gracefully if pdfplumber is not installed.
"""
import io
import re
from datetime import datetime
from decimal import Decimal

DATE_RE   = re.compile(r"\b(\d{2}[/-]\d{2}[/-]\d{4}|\d{4}-\d{2}-\d{2})\b")
AMOUNT_RE = re.compile(r"[\d,]+\.\d{2}")


def _parse_date_str(s: str):
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


class PDFParser:
    """
    Generic PDF parser — extracts text line by line and applies heuristics.
    For bank-specific layouts use the parsers in parsers/banks/.
    """

    def parse(self, file_obj, **kwargs) -> list[dict]:
        try:
            import pdfplumber
        except ImportError:
            raise ImportError(
                "pdfplumber is required for PDF parsing. "
                "Install it with: pip install pdfplumber"
            )

        content = file_obj.read()
        results = []

        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                # First try table extraction (most reliable)
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if not row:
                            continue
                        row_text = " ".join(str(c or "") for c in row)
                        tx = self._parse_row(row_text)
                        if tx:
                            results.append(tx)

                # Fall back to raw text if no tables found
                if not tables:
                    text = page.extract_text() or ""
                    for line in text.splitlines():
                        tx = self._parse_row(line)
                        if tx:
                            results.append(tx)

        return results

    def _parse_row(self, line: str) -> dict | None:
        date_match   = DATE_RE.search(line)
        amount_matches = AMOUNT_RE.findall(line)

        if not date_match or not amount_matches:
            return None

        parsed_date = _parse_date_str(date_match.group())
        if not parsed_date:
            return None

        # Use the last amount in the line as the transaction amount
        raw_amount = amount_matches[-1].replace(",", "")
        try:
            amount = float(raw_amount)
        except ValueError:
            return None

        # Simple direction heuristic: if line contains "DR" it's a debit
        direction = "credit" if re.search(r"\bCR\b", line, re.I) else "debit"

        # Description = everything before the date
        desc = line[:date_match.start()].strip()

        return {
            "merchant":    desc,
            "description": desc,
            "amount":      amount,
            "direction":   direction,
            "date":        parsed_date,
            "reference":   "",
        }
