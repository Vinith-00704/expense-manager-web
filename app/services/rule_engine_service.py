"""
app/services/rule_engine_service.py
=====================================
Modular rule engine for user-configurable transaction classification.

Rules are evaluated sequentially against a transaction dict.
First matching rule wins. Designed to accept DB-stored rules in the future.
"""
from decimal import Decimal


# ── Default built-in rules ──────────────────────────────────────────────────
# Each rule: {"condition": callable(tx) -> bool, "action": dict of overrides}
# "tx" is a dict with keys: normalized_merchant, amount, direction, category
DEFAULT_RULES: list[dict] = [
    # High-value transaction flag
    {
        "name": "high_expense_flag",
        "condition": lambda tx: (
            tx.get("direction") == "debit" and float(tx.get("amount", 0)) > 5000
        ),
        "action": {"notes": "[HIGH EXPENSE]"},
    },
    # Salary income detection
    {
        "name": "salary_credit",
        "condition": lambda tx: (
            tx.get("direction") == "credit"
            and any(kw in (tx.get("normalized_merchant") or "").lower()
                    for kw in ["salary", "payroll", "pay"])
        ),
        "action": {"category": "Salary", "entry_type": "income"},
    },
    # Refund detection
    {
        "name": "refund_credit",
        "condition": lambda tx: (
            tx.get("direction") == "credit"
            and any(kw in (tx.get("normalized_merchant") or "").lower()
                    for kw in ["refund", "reversal", "cashback"])
        ),
        "action": {"category": "Other", "notes": "[REFUND]"},
    },
]


class RuleEngine:
    """
    Evaluates a list of rules against a transaction dict.
    Returns merged overrides from all matching rules.
    Rules can be loaded from DB in future for user customisation.
    """

    def __init__(self, extra_rules: list[dict] | None = None):
        self.rules = DEFAULT_RULES + (extra_rules or [])

    def evaluate(self, transaction: dict) -> dict:
        """
        Run all rules against the transaction.

        Args:
            transaction: Dict with normalised transaction fields.

        Returns:
            Merged overrides dict (may be empty if no rules matched).
        """
        overrides = {}
        for rule in self.rules:
            try:
                if rule["condition"](transaction):
                    overrides.update(rule["action"])
            except Exception:
                continue  # bad rule must not crash the pipeline
        return overrides

    def add_rule(self, name: str, condition, action: dict) -> None:
        """Dynamically add a rule at runtime."""
        self.rules.append({"name": name, "condition": condition, "action": action})


# Module-level singleton
_engine = RuleEngine()


def evaluate(transaction: dict) -> dict:
    """Convenience wrapper around the singleton RuleEngine."""
    return _engine.evaluate(transaction)
