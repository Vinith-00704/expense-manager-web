"""
app/utils/parsers/excel_parser.py
Smart XLSX bank statement parser.

Handles the common real-world problems with Indian bank Excel exports:
  - Data doesn't start at row 0 (bank name/logo rows above the header)
  - Column headers have extra spaces or unusual capitalisation
  - Merged cells in header rows
  - Multiple sheets (picks the one with the most data rows)
  - Single "Amount" column with positive/negative values
  - Wide variety of column naming conventions
"""
import io
import logging
import pandas as pd
from decimal import Decimal, InvalidOperation
from datetime import datetime, date

log = logging.getLogger(__name__)

# ── Expanded column aliases ───────────────────────────────────────────────────
# Covers HDFC, SBI, ICICI, Axis, Kotak, Yes Bank, Federal, IndusInd exports

_DATE_ALIASES = {
    "date", "txn date", "transaction date", "value date", "posted date",
    "trans date", "tran date", "booking date", "entry date", "effective date",
    "transaction dt", "txn dt", "dt", "trans dt", "posting date",
    # Axis Bank
    "tran date", "value dt",
    # Kotak
    "transaction posting date",
    # Yes Bank
    "initiated date", "execution date",
}

_DESC_ALIASES = {
    "description", "narration", "particulars", "remarks", "details",
    "merchant", "transaction details", "transaction description",
    "transaction narration", "tran particulars", "transaction remarks",
    "beneficiary", "payee", "cheque details", "narrative",
    "transaction particular", "trans particulars", "trans description",
    # Axis Bank — exact column name in their export
    "tran particular", "transaction particular", "chq/ref.no.",
    # Kotak
    "description", "memo",
    # Yes Bank
    "transaction description",
}

_DEBIT_ALIASES = {
    "debit", "debit amount", "withdrawal", "withdrawal amount", "dr",
    "debit(inr)", "withdrawal(inr)", "debit amt", "dr amount",
    "paid out", "money out", "debit(rs.)", "withdraw", "debits",
    "debit amount(inr)", "amount debited",
    # Axis Bank — exact column names
    "withdrawal amt.", "withdrawal amt", "debit amt.",
    # Kotak
    "debit amount (inr)",
    # Federal Bank
    "debit amount (rs)",
}

_CREDIT_ALIASES = {
    "credit", "credit amount", "deposit", "deposit amount", "cr",
    "credit(inr)", "deposit(inr)", "credit amt", "cr amount",
    "paid in", "money in", "credit(rs.)", "deposits", "credits",
    "credit amount(inr)", "amount credited",
    # Axis Bank — exact column names
    "deposit amt.", "deposit amt", "credit amt.",
    # Kotak
    "credit amount (inr)",
    # Federal Bank
    "credit amount (rs)",
}

_AMOUNT_ALIASES = {
    "amount", "transaction amount", "txn amount", "trans amount",
    "amount(inr)", "amount (inr)", "amount(rs)", "amount(rs.)",
    "net amount", "transaction amt",
    # Axis Bank net balance (sometimes used as single-amount col in older exports)
    "closing balance", "balance",
}

_REF_ALIASES = {
    "reference", "ref no", "chq/ref number", "utr", "txn id",
    "reference no", "reference number", "cheque no", "cheque number",
    "transaction id", "transaction no", "ref number", "chq no",
    "transaction reference", "utr no", "rrn",
    # Axis Bank
    "chq./ref.no.", "chq/ref no", "chq./ref no.",
}

# Minimum rows to consider a sheet worth parsing
_MIN_DATA_ROWS = 2
# Max header rows to scan — set to 30 to handle Axis/Federal/Kotak
# which put 12-20 rows of account metadata before the column header
_MAX_HEADER_SCAN = 30


# ── Helpers ───────────────────────────────────────────────────────────────────

def _find_col(columns: list[str], aliases: set[str]) -> str | None:
    """Case-insensitive partial-match column finder."""
    lower_map = {c.lower().strip(): c for c in columns}
    # Exact match first
    for alias in aliases:
        if alias in lower_map:
            return lower_map[alias]
    # Partial match (alias is substring of column name)
    for alias in aliases:
        for col_lower, col_orig in lower_map.items():
            if alias in col_lower:
                return col_orig
    return None


def _parse_amount(val) -> Decimal | None:
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    try:
        cleaned = str(val).replace(",", "").replace("₹", "").replace("Rs.", "").strip()
        if cleaned in ("", "-", "nil", "n/a"):
            return None
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _parse_date(val) -> date | None:
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    for fmt in (
        "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d-%b-%Y", "%d %b %Y",
        "%m/%d/%Y", "%d/%m/%y", "%d-%m-%y", "%d %b %y", "%d-%b-%y",
        "%Y/%m/%d", "%d.%m.%Y", "%d.%m.%y",
    ):
        try:
            return datetime.strptime(str(val).strip(), fmt).date()
        except ValueError:
            continue
    return None


def _score_header_row(columns: list[str]) -> int:
    """Score how likely a row is to be the column header. Higher = better."""
    score = 0
    cols_lower = [c.lower().strip() for c in columns]

    if _find_col(columns, _DATE_ALIASES):
        score += 10
    if _find_col(columns, _DESC_ALIASES):
        score += 5
    if _find_col(columns, _DEBIT_ALIASES):
        score += 8
    if _find_col(columns, _CREDIT_ALIASES):
        score += 8
    if _find_col(columns, _AMOUNT_ALIASES):
        score += 4   # lower weight — 'balance' alone doesn't mean it's the header
    if _find_col(columns, _REF_ALIASES):
        score += 3

    # Bonus: Axis Bank specific column pattern detection
    # Their header looks like: Tran Date | Chq./Ref.No. | Transaction Remarks | Withdrawal Amt. | Deposit Amt. | Balance
    axis_hits = sum(1 for c in cols_lower if any(kw in c for kw in [
        'tran date', 'withdrawal amt', 'deposit amt', 'transaction remarks',
        'tran particular', 'chq./ref', 'chq/ref',
    ]))
    if axis_hits >= 2:
        score += axis_hits * 5   # strong signal it's an Axis Bank header row

    return score


def _try_parse_df(df: pd.DataFrame) -> list[dict] | None:
    """
    Try to extract transactions from a DataFrame.
    Returns list of dicts if successful, None otherwise.
    """
    cols = list(df.columns)
    date_col   = _find_col(cols, _DATE_ALIASES)
    desc_col   = _find_col(cols, _DESC_ALIASES)
    debit_col  = _find_col(cols, _DEBIT_ALIASES)
    credit_col = _find_col(cols, _CREDIT_ALIASES)
    amt_col    = _find_col(cols, _AMOUNT_ALIASES)
    ref_col    = _find_col(cols, _REF_ALIASES)

    if not date_col:
        return None
    if not (debit_col or credit_col or amt_col):
        return None

    results = []
    for _, row in df.iterrows():
        parsed_date = _parse_date(row.get(date_col))
        if parsed_date is None:
            continue

        desc = str(row.get(desc_col, "") or "").strip() if desc_col else ""
        ref  = str(row.get(ref_col,  "") or "").strip() if ref_col  else ""

        direction = "debit"
        amount: Decimal | None = None

        if debit_col and credit_col:
            debit  = _parse_amount(row.get(debit_col))
            credit = _parse_amount(row.get(credit_col))
            if debit and debit > 0:
                amount, direction = debit, "debit"
            elif credit and credit > 0:
                amount, direction = credit, "credit"
        elif amt_col:
            amount = _parse_amount(row.get(amt_col))
            if amount is not None and amount < 0:
                amount, direction = abs(amount), "debit"
            elif amount and amount > 0:
                direction = "credit" if credit_col else "debit"
        elif debit_col:
            amount = _parse_amount(row.get(debit_col))
            direction = "debit"
        elif credit_col:
            amount = _parse_amount(row.get(credit_col))
            direction = "credit"

        if amount is None or amount <= 0:
            continue

        results.append({
            "merchant":    desc,
            "description": desc,
            "amount":      float(amount),
            "direction":   direction,
            "date":        parsed_date,
            "reference":   ref,
        })

    return results if results else None


# ── Main parser class ─────────────────────────────────────────────────────────

class ExcelParser:
    """
    Robust XLSX bank statement parser.
    Handles header rows at any position (row 0–10) and wide column name variants.
    """

    def parse(self, file_obj, **kwargs) -> list[dict]:
        content = file_obj.read()

        # ── Auto-detect file format and choose the right engine ──────────
        # .xlsx / .xlsm  → openpyxl  (zip-based XML, modern Excel)
        # .xls            → xlrd      (binary BIFF format, Excel 97-2003)
        # .xlsb           → pyxlsb   (binary XLSB)
        # .ods            → odf       (OpenDocument)

        fname = getattr(file_obj, 'filename', '') or getattr(file_obj, 'name', '') or ''
        ext   = fname.rsplit('.', 1)[-1].lower() if '.' in fname else ''

        # Sniff magic bytes to catch mislabelled files
        magic = content[:8]
        # PK = zip (xlsx/xlsm); D0CF = OLE2 compound doc (xls)
        if magic[:2] == b'PK':
            engine = 'openpyxl'
        elif magic[:8] == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':
            engine = 'xlrd'
        elif ext == 'xls':
            engine = 'xlrd'
        elif ext in ('xlsb',):
            engine = 'pyxlsb'
        elif ext in ('ods',):
            engine = 'odf'
        else:
            engine = 'openpyxl'   # default — works for .xlsx

        try:
            xl = pd.ExcelFile(io.BytesIO(content), engine=engine)
        except Exception as exc:
            err_msg = str(exc)
            # Give a clear, actionable error instead of the raw exception
            if 'xlrd' in err_msg.lower() or 'not a zip' in err_msg.lower():
                raise ValueError(
                    "This looks like an old-format Excel file (.xls). "
                    "Please open it in Excel and save as .xlsx (Excel Workbook), "
                    "then upload again. Alternatively, export as CSV."
                ) from exc
            if 'zip file' in err_msg.lower():
                raise ValueError(
                    "Cannot open Excel file — the file may be corrupted or is not "
                    "a real Excel file. Try saving it again from Excel as .xlsx or export as CSV."
                ) from exc
            raise ValueError(f"Cannot open Excel file: {exc}") from exc


        best_result   = None
        best_rows     = 0
        debug_info    = []

        for sheet in xl.sheet_names:
            log.debug(f"Trying sheet: {sheet!r}")

            # ── Strategy 1: pandas default (header at row 0) ──────────────
            try:
                df = xl.parse(sheet, dtype=str, header=0)
                df.columns = [str(c).strip() for c in df.columns]
                result = _try_parse_df(df)
                if result and len(result) > best_rows:
                    best_result = result
                    best_rows   = len(result)
                    log.debug(f"  → Sheet {sheet!r} row-0 header: {len(result)} rows")
            except Exception as e:
                log.debug(f"  → Sheet {sheet!r} row-0 failed: {e}")

            # ── Strategy 2: scan rows 1–_MAX_HEADER_SCAN for the header ──
            try:
                raw = xl.parse(sheet, dtype=str, header=None)
                best_score = 0
                best_hrow  = None

                for hrow in range(min(_MAX_HEADER_SCAN, len(raw))):
                    candidate_cols = [str(v).strip() for v in raw.iloc[hrow].tolist()]
                    score = _score_header_row(candidate_cols)
                    if score > best_score:
                        best_score = score
                        best_hrow  = hrow

                if best_hrow is not None and best_score >= 5:
                    df2 = xl.parse(sheet, dtype=str, header=best_hrow)
                    df2.columns = [str(c).strip() for c in df2.columns]
                    result2 = _try_parse_df(df2)
                    if result2 and len(result2) > best_rows:
                        best_result = result2
                        best_rows   = len(result2)
                        log.debug(
                            f"  → Sheet {sheet!r} header at row {best_hrow} "
                            f"(score {best_score}): {len(result2)} rows"
                        )
                    debug_info.append(
                        f"Sheet {sheet!r}: best header row={best_hrow}, score={best_score}, "
                        f"cols={[str(c) for c in xl.parse(sheet, dtype=str, header=best_hrow).columns[:6]]}"
                    )
                else:
                    debug_info.append(f"Sheet {sheet!r}: no recognisable header (best score={best_score})")

            except Exception as e:
                debug_info.append(f"Sheet {sheet!r}: scan failed: {e}")

        if best_result:
            return best_result

        # Build a helpful diagnostic message
        diag = "; ".join(debug_info) if debug_info else "no sheets processed"
        raise ValueError(
            f"Could not find transaction data in the Excel file. "
            f"Diagnostic: {diag}. "
            f"Tip: Make sure your Excel has columns like Date, Description/Narration, "
            f"and Debit/Credit or Amount."
        )
