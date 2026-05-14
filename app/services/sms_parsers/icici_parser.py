"""
app/services/sms_parsers/icici_parser.py
ICICI Bank SMS parser.

Example: "ICICI Bank Acct XX1234 debited with INR 250.00 on 04-May-2026.
          Info: UPI/UBER. Avl Bal INR 8765.43"
"""
import re
from datetime import datetime


AMOUNT_RE   = re.compile(r"(?:INR|Rs\.?)\s*([\d,]+(?:\.\d{1,2})?)", re.I)
INFO_RE     = re.compile(r"Info[:\s]+([A-Za-z0-9/._\- ]{2,50})", re.I)
DATE_RE     = re.compile(r"\d{2}[/-][A-Za-z]{3}[/-]\d{2,4}")

ICICI_TRIGGERS = ["icici bank", "icici"]


def _parse_date(s: str):
    for fmt in ("%d-%b-%Y", "%d/%b/%Y", "%d-%b-%y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return datetime.today().date()


class ICICISMSParser:
    name = "icici"

    def can_parse(self, sms_text: str) -> bool:
        return any(t in sms_text.lower() for t in ICICI_TRIGGERS)

    def parse(self, sms_text: str) -> dict | None:
        amount_m = AMOUNT_RE.search(sms_text)
        if not amount_m:
            return None

        amount  = float(amount_m.group(1).replace(",", ""))
        lower   = sms_text.lower()
        direction = "credit" if "credited" in lower else "debit"

        info_m   = INFO_RE.search(sms_text)
        merchant = info_m.group(1).strip() if info_m else "ICICI Transaction"

        date_m  = DATE_RE.search(sms_text)
        tx_date = _parse_date(date_m.group()) if date_m else datetime.today().date()

        return {
            "merchant":       merchant,
            "amount":         amount,
            "direction":      direction,
            "date":           tx_date,
            "payment_method": "UPI" if "upi" in lower else "Debit Card",
            "raw_text":       sms_text,
            "parser":         self.name,
        }
