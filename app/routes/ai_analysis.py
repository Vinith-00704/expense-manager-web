"""
app/routes/ai_analysis.py
Blueprint for /api/ai/* — AI-powered analysis across the whole app.
"""
import json
import os
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..models.imported_transaction import ImportedTransaction
from ..utils.response import success, error
from ..utils.audit import log_action

ai_bp = Blueprint("ai_analysis", __name__)


# ── shared error wrapper ──────────────────────────────────────────────────────

def _ai(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except ValueError as exc:
        return error(str(exc), 422)
    except ImportError as exc:
        return error(str(exc), 422)
    except RuntimeError as exc:
        return error(str(exc), 503)
    except Exception as exc:
        return error(f"AI failed: {exc}", 500)


# ═══════════════════════════════════════════════════════════════
#  IMPORT CENTER
# ═══════════════════════════════════════════════════════════════

@ai_bp.post("/analyse-batch")
@jwt_required()
def analyse_batch():
    """POST /api/ai/analyse-batch — Analyse pending imported transactions."""
    user_id = int(get_jwt_identity())
    body    = request.get_json(silent=True) or {}
    ids     = body.get("ids", [])

    if not ids:
        return error("No transaction IDs provided.", 400)
    if len(ids) > 100:
        return error("Maximum 100 transactions per analysis request.", 400)

    txs = ImportedTransaction.query.filter(
        ImportedTransaction.id.in_(ids),
        ImportedTransaction.user_id == user_id,
        ImportedTransaction.status.in_(["pending", "duplicate"]),
    ).all()

    if not txs:
        return error("No pending transactions found for the given IDs.", 404)

    from ..services.ai_analyser_service import analyse_batch as svc
    result = _ai(svc, [t.to_dict() for t in txs])
    if isinstance(result, tuple):
        return result

    log_action(user_id, "ai_analyse", "imported_transaction", None, {
        "tx_count": len(txs), "corrections": len(result.get("corrections", {})),
    })
    return success(result, f"AI analysed {len(txs)} transaction(s).")


@ai_bp.post("/categorise")
@jwt_required()
def categorise_single():
    """POST /api/ai/categorise — Suggest category for a single transaction."""
    body      = request.get_json(silent=True) or {}
    merchant  = body.get("merchant", "").strip()
    amount    = float(body.get("amount", 0))
    direction = body.get("direction", "debit")
    context   = body.get("context", "")

    if not merchant:
        return error("merchant is required.", 400)

    from ..services.ai_analyser_service import categorise_single as svc
    result = _ai(svc, merchant, amount, direction, context)
    return result if isinstance(result, tuple) else success(result)


@ai_bp.post("/apply-corrections")
@jwt_required()
def apply_corrections():
    """POST /api/ai/apply-corrections — Bulk-apply category corrections."""
    user_id     = int(get_jwt_identity())
    corrections = (request.get_json(silent=True) or {}).get("corrections", {})

    if not corrections:
        return error("No corrections provided.", 400)

    applied = 0
    for tx_id_str, patch in corrections.items():
        try:
            tx = ImportedTransaction.query.filter_by(
                id=int(tx_id_str), user_id=user_id
            ).first()
            if tx and patch.get("category"):
                tx.category = patch["category"]
                applied += 1
        except (ValueError, TypeError):
            continue

    from ..extensions import db
    db.session.commit()
    log_action(user_id, "ai_apply_corrections", "imported_transaction", None, {"applied": applied})
    return success({"applied": applied}, f"Applied {applied} AI correction(s).")


# ═══════════════════════════════════════════════════════════════
#  DASHBOARD — Financial health score + insights
# ═══════════════════════════════════════════════════════════════

@ai_bp.get("/dashboard-insights")
@jwt_required()
def dashboard_insights():
    """GET /api/ai/dashboard-insights — Financial health score + personalised insights."""
    user_id = int(get_jwt_identity())

    from ..models.expense import Expense
    from datetime import date, timedelta

    cutoff   = date.today() - timedelta(days=30)
    expenses = Expense.query.filter(
        Expense.user_id == user_id,
        Expense.expense_date >= cutoff,
    ).order_by(Expense.expense_date.desc()).limit(100).all()

    if not expenses:
        return success({
            "health_score": None, "score_label": "INSUFFICIENT_DATA",
            "insights": ["Add some expenses to get AI insights."],
            "tip": "Start tracking your spending to unlock AI-powered financial advice.",
            "summary": "No recent transactions found.",
            "total_debit": 0, "total_credit": 0,
        })

    total_debit  = sum(float(e.amount) for e in expenses if e.entry_type == "expense")
    total_credit = sum(float(e.amount) for e in expenses if e.entry_type == "income")

    by_cat = {}
    for e in expenses:
        if e.entry_type == "expense":
            by_cat[e.category] = by_cat.get(e.category, 0) + float(e.amount)

    cat_lines = "\n".join(
        f"  {cat}: Rs.{amt:,.0f} ({amt/total_debit*100:.0f}%)"
        for cat, amt in sorted(by_cat.items(), key=lambda x: -x[1])
    ) if total_debit else "  No expenses recorded."

    from ..services.ai_analyser_service import _call_gemini
    prompt = f"""You are a personal finance AI for an Indian user. Analyse the last 30 days.

Income  : Rs.{total_credit:,.0f}
Expenses: Rs.{total_debit:,.0f}
Savings : Rs.{total_credit - total_debit:,.0f}

Spending by category:
{cat_lines}

Respond with valid JSON only (no markdown fences):
{{
  "health_score": <integer 0-100>,
  "score_label": "<EXCELLENT|GOOD|FAIR|POOR>",
  "summary": "<1 sentence, under 25 words>",
  "insights": ["<insight 1>", "<insight 2>", "<insight 3>"],
  "tip": "<1 actionable tip, under 20 words>"
}}

health_score guide: 80-100 = excellent, 60-79 = good, 40-59 = fair, 0-39 = poor.
Insights must mention actual amounts or percentages.
"""
    result = _ai(_call_gemini, prompt, json_mode=True)
    if isinstance(result, tuple):
        return result

    try:
        data = json.loads(result)
        data["total_debit"]  = round(total_debit, 2)
        data["total_credit"] = round(total_credit, 2)
        return success(data)
    except Exception:
        return success({
            "health_score": None, "score_label": "ERROR",
            "summary": str(result)[:200], "insights": [], "tip": "",
            "total_debit": round(total_debit, 2), "total_credit": round(total_credit, 2),
        })


# ═══════════════════════════════════════════════════════════════
#  BUDGETS — AI-suggested budget limits
# ═══════════════════════════════════════════════════════════════

@ai_bp.get("/suggest-budgets")
@jwt_required()
def suggest_budgets():
    """GET /api/ai/suggest-budgets — Recommend monthly budget limits from 3 months history."""
    user_id = int(get_jwt_identity())

    from ..models.expense import Expense
    from datetime import date, timedelta

    cutoff = date.today() - timedelta(days=90)
    exp_rows = Expense.query.filter(
        Expense.user_id == user_id,
        Expense.expense_date >= cutoff,
        Expense.entry_type == "expense",
    ).all()

    if not exp_rows:
        return success({"budgets": {}, "message": "No spending history. Add expenses first."})

    inc_total = sum(float(e.amount) for e in Expense.query.filter(
        Expense.user_id == user_id,
        Expense.expense_date >= cutoff,
        Expense.entry_type == "income",
    ).all())

    by_cat = {}
    for e in exp_rows:
        by_cat[e.category] = by_cat.get(e.category, 0) + float(e.amount)
    monthly_avg    = {cat: round(amt / 3, 2) for cat, amt in by_cat.items()}
    monthly_income = round(inc_total / 3, 2)

    cat_lines = "\n".join(
        f"  {cat}: avg Rs.{amt:,.0f}/month"
        for cat, amt in sorted(monthly_avg.items(), key=lambda x: -x[1])
    )

    from ..services.ai_analyser_service import _call_gemini
    prompt = f"""You are a personal finance AI advising an Indian user on monthly budget limits.

Average monthly income: Rs.{monthly_income:,.0f}
Current average monthly spending by category:
{cat_lines}

Suggest realistic but slightly reduced monthly limits using the 50/30/20 rule (50% needs, 30% wants, 20% savings).

Respond with valid JSON only:
{{
  "budgets": {{
    "<category_name>": <integer_rupee_limit>
  }},
  "rationale": "<1-2 sentences>",
  "savings_target": <integer_monthly_savings_rupees>
}}

Only include categories that were in the spending data. Use integer values.
"""
    result = _ai(_call_gemini, prompt, json_mode=True)
    if isinstance(result, tuple):
        return result

    try:
        data = json.loads(result)
        data["current_monthly_avg"] = monthly_avg
        data["monthly_income"] = monthly_income
        return success(data)
    except Exception:
        return error("AI returned an unexpected response.", 500)


# ═══════════════════════════════════════════════════════════════
#  GOALS — AI advice on reaching a specific goal
# ═══════════════════════════════════════════════════════════════

@ai_bp.post("/goal-advice")
@jwt_required()
def goal_advice():
    """POST /api/ai/goal-advice — { goal_id: N } — Advice on how to reach the goal faster."""
    user_id = int(get_jwt_identity())
    goal_id = (request.get_json(silent=True) or {}).get("goal_id")
    if not goal_id:
        return error("goal_id is required.", 400)

    from ..models.financial_goal import FinancialGoal
    from ..models.expense import Expense
    from datetime import date, timedelta

    goal = FinancialGoal.query.filter_by(id=goal_id, user_id=user_id).first()
    if not goal:
        return error("Goal not found.", 404)

    cutoff = date.today() - timedelta(days=90)
    income   = sum(float(e.amount) for e in Expense.query.filter(
        Expense.user_id == user_id, Expense.expense_date >= cutoff, Expense.entry_type == "income"
    ).all())
    expenses = sum(float(e.amount) for e in Expense.query.filter(
        Expense.user_id == user_id, Expense.expense_date >= cutoff, Expense.entry_type == "expense"
    ).all())
    avg_monthly_savings = round((income - expenses) / 3, 2)

    from ..services.ai_analyser_service import _call_gemini
    prompt = f"""You are a personal finance AI advising on reaching a savings goal.

Goal name    : {goal.name}
Category     : {goal.category}
Target amount: Rs.{float(goal.target_amount):,.0f}
Saved so far : Rs.{float(goal.current_amount or 0):,.0f}
Remaining    : Rs.{float(goal.target_amount) - float(goal.current_amount or 0):,.0f}
Progress     : {goal.progress_pct:.0f}%
Deadline     : {goal.deadline.isoformat() if goal.deadline else "No deadline"}
Days left    : {goal.days_remaining if goal.days_remaining is not None else "Open-ended"}

User average monthly savings (last 3 months): Rs.{avg_monthly_savings:,.0f}

Respond with valid JSON only:
{{
  "feasibility": "<ON_TRACK|NEEDS_EFFORT|CHALLENGING|DEADLINE_MISSED>",
  "monthly_required": <integer rupees/month needed>,
  "advice": ["<tip 1>", "<tip 2>", "<tip 3>"],
  "motivational_message": "<1 encouraging sentence, under 20 words>"
}}
"""
    result = _ai(_call_gemini, prompt, json_mode=True)
    if isinstance(result, tuple):
        return result

    try:
        data = json.loads(result)
        data["goal_name"]   = goal.name
        data["progress_pct"] = goal.progress_pct
        return success(data)
    except Exception:
        return error("AI returned an unexpected response.", 500)


# ═══════════════════════════════════════════════════════════════
#  STATUS
# ═══════════════════════════════════════════════════════════════

@ai_bp.get("/status")
@jwt_required()
def status():
    """GET /api/ai/status — Check if AI is configured."""
    has_key = bool(os.environ.get("GEMINI_API_KEY"))
    return success({
        "configured": has_key,
        "model": "gemini-2.0-flash-lite -> gemini-2.0-flash (auto-fallback)",
        "provider": "Google Gemini",
        "message": (
            "AI analysis is ready." if has_key
            else "Set GEMINI_API_KEY in your .env file. Get a free key at https://aistudio.google.com/app/apikey"
        )
    })


# =================================================================
#  EXPENSES — Deep AI insights on spending patterns
# =================================================================

@ai_bp.get("/expense-insights")
@jwt_required()
def expense_insights():
    """GET /api/ai/expense-insights?period=30|90|180"""
    user_id = int(get_jwt_identity())
    period  = min(max(int(request.args.get("period", 90)), 30), 365)

    from ..models.expense import Expense
    from datetime import date, timedelta
    from collections import defaultdict

    cutoff  = date.today() - timedelta(days=period)
    all_exp = Expense.query.filter(
        Expense.user_id == user_id,
        Expense.expense_date >= cutoff,
    ).order_by(Expense.expense_date).all()

    if not all_exp:
        return success({"has_data": False,
                        "message": "No expense data for the selected period."})

    expenses = [e for e in all_exp if e.entry_type == "expense"]
    incomes  = [e for e in all_exp if e.entry_type == "income"]
    total_spent  = sum(float(e.amount) for e in expenses)
    total_income = sum(float(e.amount) for e in incomes)
    savings      = total_income - total_spent
    savings_rate = round(savings / total_income * 100, 1) if total_income > 0 else 0

    by_cat = defaultdict(float)
    by_cat_count = defaultdict(int)
    for e in expenses:
        by_cat[e.category]       += float(e.amount)
        by_cat_count[e.category] += 1

    monthly = defaultdict(lambda: {"income": 0.0, "expense": 0.0, "count": 0})
    for e in all_exp:
        mk = e.expense_date.strftime("%Y-%m")
        k  = "income" if e.entry_type == "income" else "expense"
        monthly[mk][k] += float(e.amount)
        if e.entry_type == "expense":
            monthly[mk]["count"] += 1

    by_merchant = defaultdict(float)
    for e in expenses:
        by_merchant[e.description or "Unknown"] += float(e.amount)
    top_merchants = sorted(by_merchant.items(), key=lambda x: -x[1])[:8]
    largest       = sorted(expenses, key=lambda e: float(e.amount), reverse=True)[:5]

    months_count       = max(period / 30, 1)
    avg_monthly_spend  = round(total_spent  / months_count, 2)
    avg_monthly_income = round(total_income / months_count, 2)

    cat_lines = "\n".join(
        "  {}: Rs.{:,.0f} ({:.0f}%, {} txns)".format(
            c, a, a / total_spent * 100 if total_spent else 0, by_cat_count[c])
        for c, a in sorted(by_cat.items(), key=lambda x: -x[1])
    ) if total_spent else "  No expenses."

    month_lines = "\n".join(
        "  {}: Income Rs.{:,.0f}, Spent Rs.{:,.0f}".format(mk, v["income"], v["expense"])
        for mk, v in sorted(monthly.items())
    )
    merc_lines = "\n".join("  {}: Rs.{:,.0f}".format(m, a) for m, a in top_merchants)
    lg_lines   = "\n".join(
        "  {} | {} | Rs.{:,.0f} | {}".format(
            e.expense_date, e.description or "-", float(e.amount), e.category)
        for e in largest
    )

    prompt = (
        "Analyse this Indian user financial data. Respond ONLY with valid JSON (no markdown fences).\n\n"
        "Period: {} days | Income: Rs.{:,.0f} | Spent: Rs.{:,.0f} | "
        "Savings: Rs.{:,.0f} ({}%)\n"
        "Avg/month — Income Rs.{:,.0f}, Spend Rs.{:,.0f}\n"
        "CATEGORIES:\n{}\nMONTHLY:\n{}\nTOP MERCHANTS:\n{}\nLARGEST TXN:\n{}\n\n"
        "Return this exact JSON schema:\n"
        '{{"overall_health":"EXCELLENT|GOOD|FAIR|POOR","health_score":0,"summary":"2-3 sentences",'
        '"spending_patterns":["pattern 1","pattern 2","pattern 3"],'
        '"top_spending_category":"cat","top_spending_pct":0,'
        '"savings_assessment":"1 sentence vs 20% recommendation",'
        '"anomalies":[{{"description":"what","amount":0,"severity":"HIGH|MEDIUM|LOW"}}],'
        '"opportunities":[{{"category":"cat","action":"specific","potential_saving":0}}],'
        '"month_trend":"IMPROVING|STABLE|WORSENING","trend_reason":"why",'
        '"top_insight":"single most important insight with Rs amount",'
        '"positive_habits":["habit 1","habit 2"]}}'
    ).format(
        period, total_income, total_spent, savings, savings_rate,
        avg_monthly_income, avg_monthly_spend,
        cat_lines, month_lines, merc_lines, lg_lines
    )

    from ..services.ai_analyser_service import _call_gemini
    result = _ai(_call_gemini, prompt, json_mode=True)
    if isinstance(result, tuple):
        return result

    try:
        data = json.loads(result)
        data.update({
            "has_data": True, "period_days": period,
            "total_income": round(total_income, 2),
            "total_spent": round(total_spent, 2),
            "net_savings": round(savings, 2),
            "savings_rate": savings_rate,
            "avg_monthly_income": avg_monthly_income,
            "avg_monthly_spend": avg_monthly_spend,
            "category_breakdown": {c: round(a, 2) for c, a in by_cat.items()},
            "top_merchants": [{"name": m, "amount": round(a, 2)} for m, a in top_merchants],
        })
        log_action(user_id, "ai_expense_insights", "expense", None, {"period": period})
        return success(data)
    except Exception as exc:
        return error("AI response parse error: {}".format(exc), 500)


# =================================================================
#  SMART BUDGET — ML-inspired budget recommendations
# =================================================================

@ai_bp.get("/smart-budget")
@jwt_required()
def smart_budget():
    """GET /api/ai/smart-budget — Precise budget recommendations based on income + history."""
    user_id = int(get_jwt_identity())

    from ..models.expense import Expense
    from ..models.budget import Budget
    from datetime import date, timedelta
    from collections import defaultdict

    cutoff  = date.today() - timedelta(days=90)
    all_exp = Expense.query.filter(
        Expense.user_id == user_id,
        Expense.expense_date >= cutoff,
    ).all()

    if not all_exp:
        return success({"has_data": False, "message": "Add 1-2 months of expenses first."})

    expenses = [e for e in all_exp if e.entry_type == "expense"]
    incomes  = [e for e in all_exp if e.entry_type == "income"]
    monthly_income = round(sum(float(e.amount) for e in incomes) / 3, 2)

    by_cat = defaultdict(list)
    for e in expenses:
        by_cat[e.category].append(float(e.amount))

    cat_stats = {}
    for c, amts in by_cat.items():
        monthly_avg = sum(amts) / 3
        cat_stats[c] = {
            "monthly_avg": round(monthly_avg, 2),
            "txn_count": len(amts),
            "pct_of_income": round(monthly_avg / monthly_income * 100, 1) if monthly_income else 0,
        }

    existing = {
        b.category: float(b.monthly_limit)
        for b in Budget.query.filter_by(user_id=user_id).all()
    }

    if   monthly_income < 25000:  tier, sav = "low (<25k)", 10
    elif monthly_income < 50000:  tier, sav = "middle (25k-50k)", 20
    elif monthly_income < 100000: tier, sav = "upper-middle (50k-1L)", 25
    else:                          tier, sav = "high (>1L)", 30

    cat_lines = "\n".join(
        "  {}: Rs.{:,.0f}/mo ({} txns, {}% of income)".format(
            c, s["monthly_avg"], s["txn_count"], s["pct_of_income"])
        for c, s in sorted(cat_stats.items(), key=lambda x: -x[1]["monthly_avg"])
    )

    prompt = (
        "Create a precise monthly budget for an Indian user. "
        "Respond ONLY with valid JSON (no markdown fences).\n\n"
        "Monthly Income: Rs.{:,.0f} | Tier: {} | Target Savings: {}% = Rs.{:,.0f}\n"
        "Max Spending Budget: Rs.{:,.0f}\n"
        "CURRENT SPENDING (3-month avg):\n{}\n"
        "EXISTING BUDGETS: {}\n\n"
        "Return this exact JSON schema:\n"
        '{{"recommended_budgets":{{"<category>":{{"limit":0,"current_avg":0,"change":0,"reason":"why"}}}},'
        '"total_budget":0,"savings_target":0,"savings_pct":0,'
        '"strategy":"2-3 sentences",'
        '"priority_actions":["action 1 with Rs","action 2","action 3"],'
        '"income_allocation":{{"needs_pct":0,"wants_pct":0,"savings_pct":0}},'
        '"monthly_income":{}}}'
    ).format(
        monthly_income, tier, sav, monthly_income * sav / 100,
        monthly_income * (1 - sav / 100),
        cat_lines, existing or "None set",
        monthly_income
    )

    from ..services.ai_analyser_service import _call_gemini
    result = _ai(_call_gemini, prompt, json_mode=True)
    if isinstance(result, tuple):
        return result

    try:
        data = json.loads(result)
        data.update({
            "has_data": True,
            "monthly_income": monthly_income,
            "income_tier": tier,
            "cat_stats": cat_stats,
            "existing_budgets": existing,
        })
        log_action(user_id, "ai_smart_budget", "budget", None,
                   {"categories": len(data.get("recommended_budgets", {}))})
        return success(data)
    except Exception as exc:
        return error("AI response parse error: {}".format(exc), 500)
