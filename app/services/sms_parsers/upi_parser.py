"""
app/services/sms_parsers/upi_parser.py
Generic UPI / payment SMS parser — handles messages from PhonePe,
Google Pay, Paytm and any standard UPI provider.
"""
import re
from datetime import datetime


AMOUNT_RE  = re.compile(r"(?:Rs\.?|INR|rs\.?)\s*([\d,]+(?:\.\d{1,2})?)", re.I)
MERCHANT_RE = re.compile(
    r"(?:to|at|for|merchant|vpa|paid to)\s+([A-Za-z0-9@._\- ]{3,40})",
    re.I,
)
DATE_RE = re.compile(r"\d{2}[/-]\d{2}[/-]\d{4}|\d{4}-\d{2}-\d{2}")

UPI_TRIGGERS = [
    "upi", "gpay", "google pay", "phonepe", "paytm", "bhim",
    "upi transaction", "upi payment", "upi ref",
]


def _parse_date(s: str):
    for fmt in ("%d/%m/%Y", "%d-%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return datetime.today().date()


class UPIParser:
    name = "upi"

    def can_parse(self, sms_text: str) -> bool:
        lower = sms_text.lower()
        return any(trigger in lower for trigger in UPI_TRIGGERS)

    def parse(self, sms_text: str) -> dict | None:
        amount_match = AMOUNT_RE.search(sms_text)
        if not amount_match:
            return None

        amount = float(amount_match.group(1).replace(",", ""))
        lower  = sms_text.lower()

        direction = "credit" if any(
            w in lower for w in ["received", "credited", "credit"]
        ) else "debit"

        merchant_match = MERCHANT_RE.search(sms_text)
        merchant = merchant_match.group(1).strip() if merchant_match else "UPI Payment"

        date_match = DATE_RE.search(sms_text)
        tx_date    = _parse_date(date_match.group()) if date_match else datetime.today().date()

        return {
            "merchant":    merchant,
            "amount":      amount,
            "direction":   direction,
            "date":        tx_date,
            "payment_method": "UPI",
            "raw_text":    sms_text,
            "parser":      self.name,
        }
