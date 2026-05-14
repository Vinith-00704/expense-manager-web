"""
app/services/sms_parsers/sbi_parser.py
SBI Bank SMS parser.

Example: "Your A/c XX1234 is debited for Rs.500.00 on 03MAY26.
          Info: UPI/SWIGGY. Avl Bal: Rs.12345.00 -SBI"
"""
import re
from datetime import datetime


AMOUNT_RE   = re.compile(r"Rs\.?\s*([\d,]+(?:\.\d{1,2})?)", re.I)
INFO_RE     = re.compile(r"Info[:\s]+([A-Za-z0-9/._\- ]{2,50})", re.I)
DATE_RE     = re.compile(r"\d{2}[A-Z]{3}\d{2,4}", re.I)

SBI_TRIGGERS = ["sbi", "state bank"]


def _parse_date(s: str):
    for fmt in ("%d%b%y", "%d%b%Y"):
        try:
            return datetime.strptime(s.upper(), fmt).date()
        except ValueError:
            continue
    return datetime.today().date()


class SBISMSParser:
    name = "sbi"

    def can_parse(self, sms_text: str) -> bool:
        return any(t in sms_text.lower() for t in SBI_TRIGGERS)

    def parse(self, sms_text: str) -> dict | None:
        amount_m = AMOUNT_RE.search(sms_text)
        if not amount_m:
            return None

        amount  = float(amount_m.group(1).replace(",", ""))
        lower   = sms_text.lower()
        direction = "credit" if "credited" in lower else "debit"

        info_m   = INFO_RE.search(sms_text)
        merchant = info_m.group(1).strip() if info_m else "SBI Transaction"

        date_m  = DATE_RE.search(sms_text)
        tx_date = _parse_date(date_m.group()) if date_m else datetime.today().date()

        return {
            "merchant":       merchant,
            "amount":         amount,
            "direction":      direction,
            "date":           tx_date,
            "payment_method": "UPI" if "upi" in lower else "Net Banking",
            "raw_text":       sms_text,
            "parser":         self.name,
        }
