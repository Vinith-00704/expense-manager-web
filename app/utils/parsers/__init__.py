"""
app/utils/parsers/__init__.py
Parser registry — factory that selects the right parser for a file type.
"""
from typing import Protocol, runtime_checkable


@runtime_checkable
class StatementParser(Protocol):
    """Interface all parsers must satisfy."""

    def parse(self, file_obj, **kwargs) -> list[dict]:
        """
        Parse a file-like object and return a list of raw transaction dicts.

        Each dict must contain at minimum:
            merchant      (str)
            amount        (float)
            direction     "debit" | "credit"
            date          datetime.date
        Optionally:
            description   (str)
            reference     (str)
        """
        ...


def get_parser(file_type: str, bank: str | None = None):
    """
    Return the appropriate parser instance.

    Args:
        file_type: "csv" | "xlsx" | "pdf"
        bank:      Optional bank hint: "hdfc" | "sbi" | "icici" | "axis"

    Returns:
        Parser instance implementing StatementParser protocol.
    """
    ft = file_type.lower().lstrip(".")

    if ft == "csv":
        from .csv_parser import CSVParser
        return CSVParser()

    if ft in ("xlsx", "xls"):
        from .excel_parser import ExcelParser
        return ExcelParser()

    if ft == "pdf":
        if bank:
            bank_lower = bank.lower()
            try:
                if bank_lower == "hdfc":
                    from .banks.hdfc_parser import HDFCParser
                    return HDFCParser()
                if bank_lower == "sbi":
                    from .banks.sbi_parser import SBIParser
                    return SBIParser()
                if bank_lower == "icici":
                    from .banks.icici_parser import ICICIParser
                    return ICICIParser()
                if bank_lower == "axis":
                    from .banks.axis_parser import AXISParser
                    return AXISParser()
            except ImportError:
                pass  # fall through to generic PDF
        from .pdf_parser import PDFParser
        return PDFParser()

    raise ValueError(f"Unsupported file type: {file_type!r}")


def detect_bank(text_sample: str) -> str | None:
    """
    Attempt to detect the bank from a short text sample (first 2000 chars of PDF).
    Returns lowercase bank name or None.
    """
    sample = text_sample.lower()
    if "hdfc bank" in sample or "hdfc" in sample:
        return "hdfc"
    if "state bank of india" in sample or "sbi" in sample:
        return "sbi"
    if "icici bank" in sample or "icici" in sample:
        return "icici"
    if "axis bank" in sample or "axis" in sample:
        return "axis"
    return None
