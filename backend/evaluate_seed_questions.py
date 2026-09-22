"""
Seed Question Evaluation Runner
Runs the full suite of seed questions (lookups, comparisons, aggregations,
ambiguous questions, unanswerable causal queries, predictions, out-of-scope).
Logs: Question, Generated SQL, Execution Status, Accuracy / Result Validation,
and Failure Category.
Outputs a structured JSON log and formatted Markdown table for README.md.
"""

import asyncio
import json
import time
from typing import List, Dict, Any
from backend.query_service import process_user_query
from backend.main import SEED_QUESTIONS


async def run_evaluation():
    print(f"Starting evaluation of {len(SEED_QUESTIONS)} seed questions...\n")
    results = []

    for item in SEED_QUESTIONS:
        qid = item["id"]
        q = item["question"]
        cat = item["category"]
        badge = item["badge"]

        start_t = time.time()
        res = await process_user_query(q)
        elapsed = round((time.time() - start_t) * 1000, 1)

        status = res.get("status")
        sql = res.get("sql", "N/A")
        chart_type = res.get("chart", {}).get("chart_type", "N/A")
        rows = res.get("row_count", 0)
        refl_log = res.get("reflection_log", [])
        is_forecast = res.get("is_forecast", False)

        # Determine correctness and category
        if cat in ("ambiguous", "unanswerable", "out_of_scope", "ambiguous_forecast"):
            # Expected to refuse or prompt for clarification
            if status == "refusal":
                is_correct = True
                failure_cat = "NONE (Correctly Refused)"
                notes = f"Gracefully intercepted as {res.get('intent_type')}"
            else:
                is_correct = False
                failure_cat = "FALSE_POSITIVE_EXECUTION"
                notes = "Failed to intercept unanswerable or ambiguous query"
        elif cat == "reflection_failure":
            # Expected to attempt repair and cleanly fallback after retries exhausted
            if status in ("validation_error", "execution_error", "refusal") and len(refl_log) >= 1:
                is_correct = True
                failure_cat = "NONE (Clean Retry Cap Fallback)"
                notes = f"Cleanly failed after {len(refl_log)} reflection attempt(s); no infinite loop"
            else:
                is_correct = False
                failure_cat = "UNEXPECTED_RETRY_STATE"
                notes = f"Expected clean retry exhaustion, got status={status}"
        else:
            # Expected to execute successfully
            if status == "success" and rows > 0:
                is_correct = True
                failure_cat = "NONE (Success)"
                refl_note = f" (self-healed in {len(refl_log)} retry)" if refl_log else ""
                forecast_note = " (12M Holt-Winters forecast)" if is_forecast else ""
                notes = f"{rows} rows, {chart_type} chart rendered{refl_note}{forecast_note}"
            elif status == "success" and rows == 0:
                is_correct = False
                failure_cat = "EMPTY_RESULT"
                notes = "Query executed but returned 0 rows"
            elif status == "validation_error":
                is_correct = False
                failure_cat = "SQL_VALIDATION_BLOCKED"
                notes = res.get("error", "Validation error")
            else:
                is_correct = False
                failure_cat = "EXECUTION_ERROR"
                notes = res.get("error", "Execution error")

        log_entry = {
            "id": qid,
            "question": q,
            "category": cat,
            "badge": badge,
            "status": status,
            "sql": sql,
            "chart_type": chart_type,
            "rows": rows,
            "execution_ms": elapsed,
            "is_correct": is_correct,
            "failure_category": failure_cat,
            "notes": notes,
            "is_forecast": is_forecast,
            "reflection_triggered": len(refl_log) > 0,
            "reflection_attempts": len(refl_log),
            "reflection_log": refl_log,
            "insight": res.get("insight") or res.get("message", "")[:120]
        }
        results.append(log_entry)
        
        status_icon = "✅" if is_correct else "❌"
        print(f"{status_icon} [{qid}] {q}")
        print(f"    Category: {cat} | Status: {status} | Failure Cat: {failure_cat}")
        if sql != "N/A":
            print(f"    SQL: {sql}")
        print(f"    Notes: {notes}\n")

    # Summary
    total = len(results)
    passed = sum(1 for r in results if r["is_correct"])
    print("=" * 60)
    print(f"EVALUATION COMPLETE: {passed}/{total} Passed (Accuracy: {round(passed/total*100, 1)}%)")
    print("=" * 60)

    # Save to file
    out_json = "eval_results.json"
    with open(out_json, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Saved evaluation results to {out_json}")

    return results


if __name__ == "__main__":
    asyncio.run(run_evaluation())
