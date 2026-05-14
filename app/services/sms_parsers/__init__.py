"""
app/services/sms_parsers/__init__.py
Modular SMS parser registry.

Parser priority:
  1. HDFC   — bank-specific regex
  2. SBI    — bank-specific regex
  3. ICICI  — bank-specific regex
  4. UPI    — generic UPI regex
  5. Gemini — NLP fallback (handles any bank, any format)
"""
from typing import Protocol, runtime_checkable


@runtime_checkable
class SMSParser(Protocol):
    name: str

    def can_parse(self, sms_text: str) -> bool: ...
    def parse(self, sms_text: str) -> dict | None: ...


def get_sms_parser(sms_text: str):
    """
    Auto-select the appropriate SMS parser for the given message.
    Tries regex parsers first (fast, zero API calls), then Gemini NLP.
    Returns the first parser whose can_parse() returns True, else None.
    """
    from .upi_parser    import UPIParser
    from .hdfc_parser   import HDFCSMSParser
    from .sbi_parser    import SBISMSParser
    from .icici_parser  import ICICISMSParser
    from .gemini_parser import GeminiSMSParser

    # Regex parsers first (fast, free), Gemini last (handles anything)
    parsers = [
        HDFCSMSParser(),
        SBISMSParser(),
        ICICISMSParser(),
        UPIParser(),
        GeminiSMSParser(),   # NLP fallback
    ]

    for parser in parsers:
        if parser.can_parse(sms_text):
            return parser
    return None


def parse_sms(sms_text: str) -> dict | None:
    """Convenience: detect parser and parse in one call."""
    parser = get_sms_parser(sms_text)
    if parser:
        return parser.parse(sms_text)
    return None
