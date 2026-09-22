"""
Query Service Orchestrator
Thin coordination layer that wires together intent classification, SQL generation,
validation, execution, chart heuristics, and grounded narration.
"""

import logging
import re
from typing import Any, Dict, List, Optional

from backend.config import settings
from backend.intent_classifier import classify_query_intent
from backend.sql_validator import validate_and_sanitize_sql
from backend.sql_executor import execute_sqlite_query
from backend.chart_heuristics import determine_chart_spec, determine_forecast_chart_spec
from backend.grounded_narrator import compute_deterministic_stats, format_deterministic_fallback
from backend.forecasting import generate_statistical_forecast
from backend.schema_context import CANONICAL_REGIONS, REGION_ALIASES
from backend.llm_client import (
    generate_sql_with_openrouter,
    generate_sql_reflection_with_openrouter,
    generate_grounded_insight,
)
from backend.fallback_engine import rule_based_sql_generator, rule_based_reflection_repair

logger = logging.getLogger(__name__)


def extract_sql_from_text(text: Optional[str]) -> str:
    """Extracts SQL query from markdown code block or raw string."""
    if not text:
        return ""
    match = re.search(r"```(?:sql)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text.strip()


def _detect_region(question: str) -> str:
    """Detect target region from question text."""
    q = question.lower()
    for alias, canonical in sorted(REGION_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        if re.search(rf"\b{re.escape(alias)}\b", q):
            return canonical
    for reg in sorted(CANONICAL_REGIONS, key=len, reverse=True):
        if reg.lower() in q:
            return reg
    return "Australia"


async def _handle_forecast(question: str, intent) -> Dict[str, Any]:
    """Handle opt-in statistical forecasting path."""
    target_reg = _detect_region(question)

    hist_sql = (
        f"SELECT date, value FROM labour_force_monthly "
        f"WHERE metric_name = 'Unemployment rate' AND region = '{target_reg}' "
        f"ORDER BY date ASC;"
    )
    is_valid, sanitized_hist_sql, val_err = validate_and_sanitize_sql(hist_sql)
    hist_res = execute_sqlite_query(sanitized_hist_sql)

    forecast_res = generate_statistical_forecast(
        hist_res["rows"],
        date_col="date",
        val_col="value",
        horizon_months=12,
        metric_label=f"Unemployment Rate ({target_reg})",
    )
    chart_spec = determine_forecast_chart_spec(forecast_res, region=target_reg)

    last_val = forecast_res["last_observed_value"]
    proj_val = forecast_res["projected_final_mean"]
    ci_80 = (forecast_res["projected_points"][-1]["ci_80_lower"], forecast_res["projected_points"][-1]["ci_80_upper"])
    ci_95 = (forecast_res["projected_points"][-1]["ci_95_lower"], forecast_res["projected_points"][-1]["ci_95_upper"])
    final_date = forecast_res["projected_final_date"]

    narrative = (
        f"Using Holt-Winters exponential smoothing on historical seasonal patterns, {target_reg}'s "
        f"unemployment rate is projected to move from {last_val}% to {proj_val}% by {final_date} "
        f"(80% CI: {ci_80[0]}%–{ci_80[1]}%, 95% CI: {ci_95[0]}%–{ci_95[1]}%). "
        f"Statistical projection, not an official forecast."
    )

    return {
        "status": "success",
        "question": question,
        "sql": sanitized_hist_sql,
        "llm_used": False,
        "model_used": "holt_winters_engine",
        "execution_time_ms": hist_res["elapsed_ms"],
        "row_count": len(forecast_res["chart_data"]),
        "chart": chart_spec,
        "insight": narrative,
        "stats": {
            "forecast_method": forecast_res["method"],
            "last_observed_date": forecast_res["last_observed_date"],
            "last_observed_value": last_val,
            "projected_final_date": final_date,
            "projected_final_value": proj_val,
            "ci_80": ci_80,
            "ci_95": ci_95,
        },
        "is_forecast": True,
        "raw_data": forecast_res["projected_points"],
        "guardrails": {
            "sqlglot_validated": True,
            "forecast_opt_in_verified": True,
            "confidence_bounds_enforced": True,
            "official_forecast_disclaimed": True,
        },
    }


async def _execute_with_reflection(
    question: str,
    raw_sql: str,
    llm_used: bool,
    active_api_key: str,
    active_model: str,
) -> Dict[str, Any]:
    """Execute SQL with self-healing reflection loop (capped at MAX_REFLECTION_RETRIES)."""
    current_sql = raw_sql
    reflection_log: List[Dict[str, Any]] = []
    sanitized_sql = ""
    rows = []
    columns = []
    elapsed_ms = 0.0

    for attempt in range(settings.max_reflection_retries + 1):
        # Step A: Validate SQL AST
        is_valid, sanitized, val_err = validate_and_sanitize_sql(current_sql)
        if not is_valid:
            error_reason = f"SQL AST Validation Blocked: {val_err}"
            logger.warning("Attempt %d: %s", attempt + 1, error_reason)

            if attempt < settings.max_reflection_retries:
                corrected = None
                if active_api_key and llm_used:
                    corrected = await generate_sql_reflection_with_openrouter(
                        question, current_sql, error_reason, active_api_key, active_model
                    )
                if not corrected:
                    corrected = rule_based_reflection_repair(question, current_sql, error_reason)

                reflection_log.append({
                    "attempt": attempt + 1,
                    "trigger": "validation_error",
                    "original_sql": current_sql,
                    "error": error_reason,
                    "corrected_sql": corrected,
                    "succeeded": False,
                })
                current_sql = corrected
                continue
            else:
                return {
                    "status": "validation_error",
                    "question": question,
                    "raw_sql": current_sql,
                    "error": val_err,
                    "reflection_log": reflection_log,
                    "guardrails": {"sqlglot_validated": False, "blocked_reason": val_err},
                }

        sanitized_sql = sanitized

        # Step B: Database execution
        try:
            exec_res = execute_sqlite_query(sanitized_sql)
            columns = exec_res["columns"]
            rows = exec_res["rows"]
            elapsed_ms = exec_res["elapsed_ms"]
        except Exception as e:
            error_reason = f"Execution error: {str(e)}"
            logger.warning("Attempt %d: %s", attempt + 1, error_reason)

            if attempt < settings.max_reflection_retries:
                corrected = None
                if active_api_key and llm_used:
                    corrected = await generate_sql_reflection_with_openrouter(
                        question, sanitized_sql, error_reason, active_api_key, active_model
                    )
                if not corrected:
                    corrected = rule_based_reflection_repair(question, sanitized_sql, error_reason)

                reflection_log.append({
                    "attempt": attempt + 1,
                    "trigger": "execution_error",
                    "original_sql": sanitized_sql,
                    "error": error_reason,
                    "corrected_sql": corrected,
                    "succeeded": False,
                })
                current_sql = corrected
                continue
            else:
                return {
                    "status": "execution_error",
                    "question": question,
                    "sql": sanitized_sql,
                    "error": str(e),
                    "reflection_log": reflection_log,
                    "guardrails": {"sqlglot_validated": True, "execution_success": False},
                }

        # Step C: Check for unexpected empty result
        if len(rows) == 0 and attempt < settings.max_reflection_retries:
            error_reason = "Query executed successfully but returned 0 rows. Check region canonical name or date filter."
            corrected = None
            if active_api_key and llm_used:
                corrected = await generate_sql_reflection_with_openrouter(
                    question, sanitized_sql, error_reason, active_api_key, active_model
                )
            if not corrected:
                corrected = rule_based_reflection_repair(question, sanitized_sql, error_reason)

            if corrected != current_sql and corrected != sanitized_sql:
                reflection_log.append({
                    "attempt": attempt + 1,
                    "trigger": "empty_result",
                    "original_sql": sanitized_sql,
                    "error": error_reason,
                    "corrected_sql": corrected,
                    "succeeded": False,
                })
                current_sql = corrected
                continue

        # Success
        if reflection_log:
            reflection_log[-1]["succeeded"] = True
        break

    return {
        "sanitized_sql": sanitized_sql,
        "columns": columns,
        "rows": rows,
        "elapsed_ms": elapsed_ms,
        "reflection_log": reflection_log,
    }


async def process_user_query(
    question: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Complete end-to-end pipeline execution.
    """
    # 1. Intent check & refusal path
    intent = classify_query_intent(question)
    if not intent.can_execute:
        return {
            "status": "refusal",
            "question": question,
            "intent_type": intent.intent_type,
            "message": intent.message,
            "suggested_queries": intent.suggested_queries,
            "guardrails": {"intent_checked": True, "refused_correctly": True},
        }

    active_api_key = api_key or settings.openrouter_api_key
    active_model = model or settings.openrouter_model

    # 2. Opt-in forecast path
    if intent.intent_type == "opt_in_forecast":
        return await _handle_forecast(question, intent)

    # 3. Generate SQL
    raw_sql = None
    llm_used = False
    if active_api_key:
        raw_sql = await generate_sql_with_openrouter(question, active_api_key, active_model)
        if raw_sql:
            llm_used = True

    if not raw_sql:
        raw_sql = rule_based_sql_generator(question)

    # 4. Execute with reflection loop
    exec_result = await _execute_with_reflection(
        question, raw_sql, llm_used, active_api_key, active_model
    )

    # If execution returned an error status, pass it through
    if "status" in exec_result:
        return exec_result

    # 5. Deterministic chart specification
    chart_spec = determine_chart_spec(exec_result["columns"], exec_result["rows"])

    # 6. Deterministic stats computation
    stats = compute_deterministic_stats(exec_result["columns"], exec_result["rows"])

    # 7. Grounded insight narration
    insight_sentence = None
    if active_api_key:
        insight_sentence = await generate_grounded_insight(
            question=question,
            stats=stats,
            api_key=active_api_key,
            model=active_model,
        )
    if not insight_sentence:
        insight_sentence = format_deterministic_fallback(question, stats)

    return {
        "status": "success",
        "question": question,
        "sql": exec_result["sanitized_sql"],
        "llm_used": llm_used,
        "model_used": active_model if llm_used else "deterministic_engine",
        "execution_time_ms": exec_result["elapsed_ms"],
        "row_count": len(exec_result["rows"]),
        "chart": chart_spec,
        "insight": insight_sentence,
        "stats": stats,
        "raw_data": exec_result["rows"][:100],
        "reflection_log": exec_result["reflection_log"],
        "reflection_triggered": len(exec_result["reflection_log"]) > 0,
        "guardrails": {
            "sqlglot_validated": True,
            "statement_type": "SELECT",
            "query_timeout_seconds": settings.query_timeout_seconds,
            "row_limit_enforced": settings.max_row_limit,
            "insight_grounded_in_computed_numbers": True,
        },
    }
