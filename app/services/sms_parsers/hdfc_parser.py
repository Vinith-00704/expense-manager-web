"""
app/services/sms_parsers/hdfc_parser.py
HDFC Bank SMS parser.
Handles debit card, credit card, and UPI messages from HDFC.

Example messages:
"Rs.540 spent on HDFC Bank Card XX1234 at SWIGGY on 04-05-26."
"HDFC Bank: Rs.1500.00 debited from A/c XX9876 on 03-05-26 to VPA xyz@upi."
"""
import re
from datetime import datetime


AMOUNT_RE   = re.compile(r"Rs\.?\s*([\d,]+(?:\.\d{1,2})?)", re.I)
MERCHANT_RE = re.compile(r"(?:at|to VPA|to)\s+([A-Za-z0-9@._\- ]{2,40})", re.I)
DATE_RE     = re.compile(r"\d{2}[/-]\d{2}[/-]\d{2,4}")

HDFC_TRIGGERS = ["hdfc bank", "hdfc", "hdfcbank"]


def _parse_date(s: str):
    for fmt in ("%d-%m-%y", "%d-%m-%Y", "%d/%m/%y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return datetime.today().date()


class HDFCSMSParser:
    name = "hdfc"

    def can_parse(self, sms_text: str) -> bool:
        return any(t in sms_text.lower() for t in HDFC_TRIGGERS)

    def parse(self, sms_text: str) -> dict | None:
        amount_m = AMOUNT_RE.search(sms_text)
        if not amount_m:
            return None

        amount  = float(amount_m.group(1).replace(",", ""))
        lower   = sms_text.lower()
        direction = "credit" if any(
            w in lower for w in ["credited", "received", "credit"]
        ) else "debit"

        merch_m  = MERCHANT_RE.search(sms_text)
        merchant = merch_m.group(1).strip() if merch_m else "HDFC Transaction"

        date_m  = DATE_RE.search(sms_text)
        tx_date = _parse_date(date_m.group()) if date_m else datetime.today().date()

        payment_method = "UPI" if "vpa" in lower else (
            "Credit Card" if "credit card" in lower else "Debit Card"
        )

        return {
            "merchant":       merchant,
            "amount":         amount,
            "direction":      direction,
            "date":           tx_date,
            "payment_method": payment_method,
            "raw_text":       sms_text,
            "parser":         self.name,
        }
