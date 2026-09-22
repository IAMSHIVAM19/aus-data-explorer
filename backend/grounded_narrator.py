"""
Grounded Insight Narrator
Computes deterministic descriptive statistics in Python code from query results,
then prompts the LLM (OpenRouter) or uses a deterministic template to express
ONLY those pre-computed numbers in a clear factual sentence.
The LLM is NEVER allowed or asked to calculate or invent numbers.
"""

from typing import List, Dict, Any, Optional
import httpx
import json


def compute_deterministic_stats(columns: List[str], rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes rigorous descriptive metrics directly in code.
    """
    if not rows:
        return {"count": 0, "summary": "No data returned."}

    stats: Dict[str, Any] = {
        "count": len(rows),
        "columns": columns
    }

    # Find numeric and date/categorical columns
    num_cols = [c for c in columns if any(isinstance(r.get(c), (int, float)) for r in rows)]
    date_cols = [c for c in columns if "date" in c.lower() or "period" in c.lower() or c.lower() == "year"]
    cat_cols = [c for c in columns if c not in num_cols and c not in date_cols]

    if not num_cols:
        return stats

    primary_num = num_cols[0]
    stats["metric_column"] = primary_num
    
    # Filter rows with non-null values for primary numeric
    valid_rows = [r for r in rows if isinstance(r.get(primary_num), (int, float))]
    if not valid_rows:
        return stats

    values = [r[primary_num] for r in valid_rows]
    min_val = min(values)
    max_val = max(values)
    avg_val = sum(values) / len(values)

    min_row = next(r for r in valid_rows if r[primary_num] == min_val)
    max_row = next(r for r in valid_rows if r[primary_num] == max_val)

    stats["min"] = {
        "value": min_val,
        "region": min_row.get("region"),
        "date": min_row.get("date") or min_row.get("year")
    }
    stats["max"] = {
        "value": max_val,
        "region": max_row.get("region"),
        "date": max_row.get("date") or max_row.get("year")
    }
    stats["average"] = round(avg_val, 2)

    # Time series trends
    if date_cols and len(valid_rows) > 1:
        time_col = date_cols[0]
        sorted_by_time = sorted(valid_rows, key=lambda x: str(x.get(time_col, "")))
        earliest = sorted_by_time[0]
        latest = sorted_by_time[-1]

        earliest_val = earliest[primary_num]
        latest_val = latest[primary_num]
        abs_change = round(latest_val - earliest_val, 2)
        pct_change = round(((latest_val - earliest_val) / earliest_val) * 100, 1) if earliest_val != 0 else 0.0

        stats["time_series"] = {
            "time_column": time_col,
            "start_period": earliest.get(time_col),
            "start_value": earliest_val,
            "end_period": latest.get(time_col),
            "end_value": latest_val,
            "absolute_change": abs_change,
            "percentage_change": pct_change
        }

    # Group rankings (if region or categorical present)
    if cat_cols:
        cat_col = cat_cols[0]
        stats["ranking"] = {
            "top": [
                {"label": str(r.get(cat_col)), "value": r[primary_num], "date": r.get("date") or r.get("year")}
                for r in sorted(valid_rows, key=lambda x: x[primary_num], reverse=True)[:3]
            ],
            "bottom": [
                {"label": str(r.get(cat_col)), "value": r[primary_num], "date": r.get("date") or r.get("year")}
                for r in sorted(valid_rows, key=lambda x: x[primary_num])[:3]
            ]
        }

    return stats


def format_deterministic_fallback(question: str, stats: Dict[str, Any]) -> str:
    """
    Template fallback if OpenRouter is unreachable or not configured.
    Guarantees 100% factual accuracy from the computed stats.
    """
    if stats.get("count", 0) == 0:
        return "No records were found matching this query in the official Australian labour dataset."

    metric_name = stats.get("metric_column", "value").replace("_", " ")
    is_rate = "rate" in metric_name.lower()
    unit = "%" if is_rate else ""

    if stats.get("count") == 1:
        max_info = stats.get("max", {})
        val = max_info.get("value")
        reg = max_info.get("region")
        dt = max_info.get("date")
        ctx = f" for {reg}" if reg else ""
        ctx += f" in {dt}" if dt else ""
        return f"The recorded {metric_name}{ctx} is {val}{unit}."

    ts = stats.get("time_series")
    if ts:
        start_p = ts["start_period"]
        end_p = ts["end_period"]
        start_v = ts["start_value"]
        end_v = ts["end_value"]
        delta = ts["absolute_change"]
        direction = "increased" if delta > 0 else ("decreased" if delta < 0 else "remained steady")
        abs_delta = abs(delta)

        change_phrase = f"by {abs_delta} percentage points" if is_rate else f"by {abs_delta:g} ({abs(ts['percentage_change'])}%)"

        return (
            f"Between {start_p} and {end_p}, {metric_name} {direction} {change_phrase} "
            f"from {start_v}{unit} to {end_v}{unit} (peaking at {stats['max']['value']}{unit} in {stats['max']['date']})."
        )

    ranking = stats.get("ranking")
    if ranking and ranking.get("top"):
        top_item = ranking["top"][0]
        return (
            f"The highest recorded {metric_name} was {top_item['value']}{unit} in {top_item['label']}"
            f" (average across group: {stats.get('average')}{unit})."
        )

    return f"The average {metric_name} is {stats.get('average')}{unit}, ranging from a minimum of {stats['min']['value']}{unit} to a maximum of {stats['max']['value']}{unit}."


async def generate_grounded_insight_openrouter(
    question: str,
    stats: Dict[str, Any],
    api_key: Optional[str],
    model: str = "meta-llama/llama-3.3-70b-instruct:free"
) -> str:
    """
    Prompts OpenRouter LLM with rigid grounding instructions to articulate
    the insight strictly using the supplied stats dict.
    """
    if not api_key:
        return format_deterministic_fallback(question, stats)

    system_prompt = (
        "You are an analytical narrator presenting official Australian Bureau of Statistics (ABS) labour data.\n"
        "You are given a user question and a STRICT JSON dictionary of PRE-COMPUTED statistics extracted directly from the database.\n\n"
        "STRICT GUARDRAILS:\n"
        "1. Formulate 1 to 2 clear, natural sentences answering the user's question.\n"
        "2. State ONLY figures, dates, and regions that explicitly exist in the COMPUTED_STATS JSON.\n"
        "3. You are FORBIDDEN from calculating, estimating, or introducing ANY other numbers.\n"
        "4. Never invent causes or assumptions. Stick purely to the supplied data."
    )

    user_prompt = (
        f"User Question: {question}\n\n"
        f"COMPUTED_STATS:\n{json.dumps(stats, indent=2)}\n\n"
        f"Generate the grounded insight sentence:"
    )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://github.com/aus-gov-data-explorer",
                "X-Title": "Aus Gov Data Explorer",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 150
            }
            resp = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
            if resp.status_code == 200:
                msg = data["choices"][0]["message"]
                content = (msg.get("content") or "").strip()
                if content:
                    return content
            else:
                print(f"[OpenRouter Narration Warning] Status {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"[OpenRouter Narration Exception]: {e}")

    # Seamless fallback
    return format_deterministic_fallback(question, stats)
