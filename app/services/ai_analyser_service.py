"""
app/services/ai_analyser_service.py
=====================================
Gemini-powered AI analyser for the Import Center.

Capabilities:
  1. Smart batch analysis -- categorise + summarise a batch of imports
  2. Per-transaction category correction
  3. Anomaly detection with natural-language explanations
  4. Merchant intent inference

Uses:  google-genai (new SDK)  +  gemini-2.0-flash  (free tier)
Free tier limits: 15 RPM, 1 million tokens/day
Get a free key: https://aistudio.google.com/app/apikey
"""
import os
import json
import logging

log = logging.getLogger(__name__)

# Models to try in order — each has its own separate free-tier quota
_MODELS = [
    "gemini-2.0-flash-lite",   # Fastest, lightest, separate quota
    "gemini-2.0-flash",        # More capable, separate quota
    "gemini-flash-latest",     # Alias, fallback
]


# ── Gemini client (lazy-loaded, new google-genai SDK) ────────────────────────

def _get_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise ValueError(
            "GEMINI_API_KEY not set in .env. "
            "Get a free key at https://aistudio.google.com/app/apikey"
        )
    return key


def _call_gemini(prompt: str, json_mode: bool = False) -> str:
    """
    Call Gemini and return the text response.
    Tries each model in _MODELS; falls back on quota errors.
    """
    try:
        from google import genai
        from google.genai import types
        from google.genai.errors import ClientError
    except ImportError:
        raise ImportError(
            "google-genai not installed. "
            "Run: .venv/Scripts/pip install google-genai"
        )

    client = genai.Client(api_key=_get_api_key())

    config = types.GenerateContentConfig(
        temperature=0.2,
        max_output_tokens=2048,
        response_mime_type="application/json" if json_mode else "text/plain",
    )

    last_error = None
    for model in _MODELS:
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=config,
            )
            log.debug(f"Gemini responded using model: {model}")
            return response.text.strip()
        except ClientError as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                log.warning(f"Quota exceeded for {model}, trying next model...")
                last_error = e
                continue
            raise   # Other errors (auth, bad request) — don't retry

    # All models exhausted
    raise RuntimeError(
        f"All Gemini models hit quota limits. "
        f"Please wait a few minutes and try again. Last error: {last_error}"
    )


# ── Public API ────────────────────────────────────────────────────────────────

CATEGORIES = [
    "Food & Dining", "Transportation", "Shopping", "Bills & Utilities",
    "Healthcare", "Entertainment", "Education", "Travel",
    "Investments", "Home & Rent", "Personal Care", "Salary",
    "Freelance", "Business", "Gift", "Other"
]


def analyse_batch(transactions: list[dict]) -> dict:
    """
    Send a batch of imported transactions to Gemini for smart analysis.

    Args:
        transactions: List of dicts with keys:
            id, merchant, normalized_merchant, amount, direction,
            transaction_date, category, confidence_score

    Returns:
        {
          "summary":    str,          # Natural-language spending summary
          "insights":   [str],        # Actionable insights
          "corrections": {            # Suggested category corrections
            "tx_id": {"category": str, "reason": str}
          },
          "anomalies":  [             # Unusual transactions
            {"id": int, "merchant": str, "amount": float, "reason": str}
          ],
          "top_merchants": [str],
          "total_debit":  float,
          "total_credit": float,
        }
    """
    if not transactions:
        return {"summary": "No transactions to analyse.", "insights": [], "corrections": {}, "anomalies": []}

    # Build a compact representation for the prompt
    tx_lines = []
    total_debit  = 0.0
    total_credit = 0.0
    for tx in transactions[:50]:  # Cap at 50 to stay within token limits
        amt = float(tx.get("amount", 0))
        direction = tx.get("direction", "debit")
        if direction == "debit":
            total_debit += amt
        else:
            total_credit += amt
        tx_lines.append(
            f"ID:{tx['id']} | {tx.get('transaction_date','')} | "
            f"{tx.get('normalized_merchant') or tx.get('merchant','')} | "
            f"{direction.upper()} {amt:.2f} | current_cat:{tx.get('category','Other')}"
        )

    tx_block = "\n".join(tx_lines)
    cats_str  = ", ".join(CATEGORIES)

    prompt = f"""You are an expert personal finance AI assistant for an Indian user.
Analyse these bank transactions and respond ONLY with valid JSON (no markdown, no explanation outside JSON).

TRANSACTIONS:
{tx_block}

VALID CATEGORIES: {cats_str}

Respond with this exact JSON structure:
{{
  "summary": "2-3 sentence spending overview in plain English",
  "insights": ["insight 1", "insight 2", "insight 3"],
  "corrections": {{
    "TX_ID": {{"category": "Correct Category", "reason": "why"}}
  }},
  "anomalies": [
    {{"id": TX_ID, "merchant": "name", "amount": 0.00, "reason": "why it's unusual"}}
  ],
  "top_merchants": ["merchant1", "merchant2", "merchant3"]
}}

Rules:
- Only include corrections where current_cat is WRONG. Use exact category names from the valid list.
- Anomalies = unusually high amounts or suspicious patterns.
- Insights should be actionable (e.g. "You spent 40% of income on food this week").
- Keep summary under 60 words.
- Return valid JSON only, no ```json fences.
"""

    try:
        raw = _call_gemini(prompt, json_mode=True)
        # Strip any accidental markdown fences just in case
        raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        result = json.loads(raw)
        result["total_debit"]  = round(total_debit,  2)
        result["total_credit"] = round(total_credit, 2)
        return result
    except json.JSONDecodeError as e:
        log.warning(f"Gemini returned invalid JSON: {e}\nRaw: {raw[:300]}")
        return {
            "summary": "AI analysis completed but response format was unexpected.",
            "insights": [],
            "corrections": {},
            "anomalies": [],
            "top_merchants": [],
            "total_debit":  round(total_debit,  2),
            "total_credit": round(total_credit, 2),
        }
    except Exception as e:
        log.error(f"Gemini API error: {e}")
        raise


def categorise_single(merchant: str, amount: float, direction: str, context: str = "") -> dict:
    """
    Ask Gemini to categorise a single transaction.

    Returns: {"category": str, "confidence": float, "reason": str}
    """
    cats_str = ", ".join(CATEGORIES)
    prompt = f"""Categorise this Indian bank transaction. Respond with valid JSON only.

Merchant: {merchant}
Amount: ₹{amount:.2f}
Type: {direction} (debit=expense, credit=income)
Context: {context or "none"}

Valid categories: {cats_str}

JSON response:
{{"category": "Category Name", "confidence": 0.95, "reason": "brief reason"}}"""

    try:
        raw  = _call_gemini(prompt).strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        data = json.loads(raw)
        # Validate category
        if data.get("category") not in CATEGORIES:
            data["category"] = "Other"
        return data
    except Exception:
        return {"category": "Other", "confidence": 0.0, "reason": "AI categorisation failed"}


def generate_import_summary(batch_result: dict, filename: str) -> str:
    """
    Generate a human-friendly one-paragraph summary of an import session.
    Used after file upload completes.
    """
    total    = batch_result.get("total_parsed", 0)
    success  = batch_result.get("pending_created", 0)
    dupes    = batch_result.get("duplicates", 0)
    bank     = batch_result.get("bank_detected") or "your bank"

    prompt = f"""Write a single friendly sentence (under 20 words) confirming:
- File from {bank} imported
- {success} new transactions found (out of {total} total)
- {dupes} duplicates skipped
Style: concise, positive, no emojis."""

    try:
        return _call_gemini(prompt)
    except Exception:
        return f"Imported {success} transactions from {bank}. {dupes} duplicates skipped."
