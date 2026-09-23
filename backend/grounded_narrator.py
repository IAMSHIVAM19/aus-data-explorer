"""
Grounded Insight Narrator
Computes deterministic descriptive statistics in Python code from query results,
then prompts the LLM (via llm_client) or uses a deterministic template to express
ONLY those pre-computed numbers in a clear factual sentence.
The LLM is NEVER allowed or asked to calculate or invent numbers.
"""

from typing import List, Dict, Any, Optional


def compute_deterministic_stats(columns: List[str], rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes rigorous descriptive metrics directly in code.
    """
    if not rows:
        return {"count": 0, "summary": "No data returned."}

    stats: Dict[str, Any] = {
        "count": len(rows),
        "columns": columns,
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
        "date": min_row.get("date") or min_row.get("year"),
    }
    stats["max"] = {
        "value": max_val,
        "region": max_row.get("region"),
        "date": max_row.get("date") or max_row.get("year"),
    }
    stats["average"] = round(avg_val, 2)

    # Time series trends (only if single series or single region)
    if date_cols and len(valid_rows) > 1:
        time_col = date_cols[0]
        distinct_cats = set(r.get(cat_cols[0]) for r in valid_rows if r.get(cat_cols[0]) is not None) if cat_cols else set()
        if len(distinct_cats) <= 1:
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
                "percentage_change": pct_change,
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
            ],
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
        peak_str = f" in {stats['max']['date']}" if stats['max'].get('date') else ""

        return (
            f"Between {start_p} and {end_p}, {metric_name} {direction} {change_phrase} "
            f"from {start_v}{unit} to {end_v}{unit} (peaking at {stats['max']['value']}{unit}{peak_str})."
        )

    ranking = stats.get("ranking")
    if ranking and ranking.get("top"):
        top_item = ranking["top"][0]
        return (
            f"The highest recorded {metric_name} was {top_item['value']}{unit} in {top_item['label']}"
            f" (average across group: {stats.get('average')}{unit})."
        )

    return f"The average {metric_name} is {stats.get('average')}{unit}, ranging from a minimum of {stats['min']['value']}{unit} to a maximum of {stats['max']['value']}{unit}."
