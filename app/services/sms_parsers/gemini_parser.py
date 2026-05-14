"""
app/services/sms_parsers/gemini_parser.py
==========================================
Gemini NLP-powered fallback SMS parser.

Used when all bank-specific regex parsers fail. Understands:
  - Any Indian bank (Axis, Kotak, Yes Bank, IndusInd, Federal, etc.)
  - UPI / NEFT / IMPS / RTGS / ATM / PoS / E-commerce
  - Credit card alerts
  - Wallet transactions (Paytm, PhonePe, GPay)
  - OTP messages (correctly returns None instead of parsing them)
"""
import logging
import json
import re
from datetime import datetime, date

log = logging.getLogger(__name__)

_JUNK_PATTERNS = [
    r'\botp\b', r'\bpassword\b', r'\bpin\b', r'\bverif', r'\bpromo\b',
    r'\boffer\b', r'\bcashback offer\b', r'\brecharge offer\b',
    r'\byour \w+ is \d{4,8}\b',
]
_JUNK_RE = re.compile('|'.join(_JUNK_PATTERNS), re.IGNORECASE)


class GeminiSMSParser:
    """Gemini-powered SMS parser — handles any bank format via NLP."""
    name = "gemini_nlp"

    def can_parse(self, sms_text: str) -> bool:
        """Only handle messages that look like bank transactions, not OTPs."""
        if _JUNK_RE.search(sms_text):
            return False
        # Must mention money-related words
        money_re = re.compile(
            r'\b(rs\.?|inr|credited|debited|withdrawn|spent|paid|received|'
            r'transfer|upi|neft|imps|rtgs|atm|pos|balance|avl bal|a/c)\b',
            re.IGNORECASE
        )
        return bool(money_re.search(sms_text))

    def parse(self, sms_text: str) -> dict | None:
        """
        Use Gemini to extract transaction details from any bank SMS.
        Returns a dict compatible with the FinanceOS transaction schema.
        """
        try:
            from ..ai_analyser_service import _call_gemini
        except ImportError:
            log.warning("AI analyser service not available.")
            return None

        prompt = f"""You are a bank SMS parser for an Indian bank. Extract transaction details from this SMS.

SMS: "{sms_text}"

Respond with valid JSON only (no markdown):
{{
  "is_transaction": true or false,
  "amount": <number or null>,
  "direction": "debit" or "credit",
  "merchant": "<merchant/payee name or null>",
  "bank": "<bank name or null>",
  "account_last4": "<last 4 digits or null>",
  "date": "<YYYY-MM-DD or null>",
  "payment_method": "<UPI|NEFT|IMPS|RTGS|ATM|Card|NetBanking|Wallet|Other>",
  "balance": <remaining balance or null>,
  "reference": "<transaction ref/UTR number or null>"
}}

Rules:
- is_transaction = false for OTPs, promos, offers, missed calls
- direction: credited/received/deposited = credit; debited/paid/withdrawn/spent = debit
- merchant: extract actual merchant name (e.g. "SWIGGY", "AMAZON", "ELECTRICITY BOARD"); if UPI, use UPI ID recipient name
- date: today if not mentioned; format YYYY-MM-DD
- amount: numeric only, no currency symbols
- Return null for any field you cannot determine"""

        try:
            raw = _call_gemini(prompt, json_mode=True)
            raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            data = json.loads(raw)
        except Exception as e:
            log.warning(f"Gemini SMS parse failed: {e}")
            return None

        if not data.get("is_transaction"):
            return None

        amount = data.get("amount")
        if not amount or float(amount) <= 0:
            return None

        # Parse date
        tx_date = date.today()
        if data.get("date"):
            try:
                tx_date = datetime.strptime(data["date"], "%Y-%m-%d").date()
            except ValueError:
                pass

        merchant = data.get("merchant") or data.get("bank") or "Unknown"

        return {
            "amount":         float(amount),
            "direction":      data.get("direction", "debit"),
            "merchant":       merchant,
            "date":           tx_date,
            "payment_method": data.get("payment_method", "Other"),
            "bank":           data.get("bank"),
            "account_last4":  data.get("account_last4"),
            "balance":        data.get("balance"),
            "reference":      data.get("reference"),
            "parser":         "gemini_nlp",
        }
