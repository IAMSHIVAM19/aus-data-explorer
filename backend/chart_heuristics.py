"""
Deterministic Chart Selection Heuristics
Analyzes query column types, names, and data cardinality to choose
optimal visualizations (Line chart, Bar chart, Multi-line, KPI card, Table)
in pure deterministic code without LLM hallucinations.
"""

from typing import List, Dict, Any, Optional
import re


def detect_column_types(columns: List[str], rows: List[Dict[str, Any]]) -> Dict[str, str]:
    types = {}
    date_patterns = re.compile(r"^\d{4}-\d{2}(-\d{2})?$")

    for col in columns:
        col_lower = col.lower()
        if "date" in col_lower or "month" in col_lower or "period" in col_lower:
            types[col] = "date"
            continue
        
        # Check values
        sample_vals = [r[col] for r in rows if r.get(col) is not None][:20]
        if not sample_vals:
            types[col] = "unknown"
            continue

        if all(isinstance(v, (int, float)) for v in sample_vals):
            # Check if it's year
            if col_lower == "year" or (all(isinstance(v, int) and 1900 <= v <= 2100 for v in sample_vals)):
                types[col] = "year"
            else:
                types[col] = "numeric"
        elif all(isinstance(v, str) and date_patterns.match(v.strip()) for v in sample_vals):
            types[col] = "date"
        else:
            types[col] = "categorical"

    return types


def determine_chart_spec(columns: List[str], rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Deterministically computes the chart specification for the frontend.
    """
    if not rows:
        return {
            "chart_type": "empty",
            "title": "No Data Found",
            "data": []
        }

    col_types = detect_column_types(columns, rows)
    date_cols = [c for c, t in col_types.items() if t in ("date", "year")]
    numeric_cols = [c for c, t in col_types.items() if t == "numeric"]
    categorical_cols = [c for c, t in col_types.items() if t == "categorical"]

    # 1. Single scalar result -> KPI Card
    if len(rows) == 1 and len(columns) <= 2 and len(numeric_cols) >= 1:
        num_col = numeric_cols[0]
        val = rows[0][num_col]
        label_col = [c for c in columns if c != num_col]
        label = f"{rows[0][label_col[0]]} - {num_col}" if label_col else num_col
        unit = "%" if ("rate" in num_col.lower() or "ratio" in num_col.lower() or "pct" in num_col.lower()) else ""
        return {
            "chart_type": "kpi",
            "title": label.replace("_", " ").title(),
            "kpi_value": val,
            "kpi_unit": unit,
            "kpi_label": label,
            "data": rows
        }

    # 2. Time series present (date / year) -> Line Chart
    if date_cols and numeric_cols:
        time_col = date_cols[0]
        num_col = numeric_cols[0]

        # Check if there is a categorical grouping column (e.g. region or metric_name)
        if categorical_cols:
            group_col = categorical_cols[0]
            distinct_groups = list(dict.fromkeys(r[group_col] for r in rows if r.get(group_col)))
            
            # If multiple groups exist (e.g. comparing NSW and Victoria), pivot for multi-line
            if len(distinct_groups) > 1 and len(distinct_groups) <= 12:
                pivoted: Dict[str, Dict[str, Any]] = {}
                for r in rows:
                    t_val = str(r[time_col])
                    grp_val = str(r[group_col])
                    if t_val not in pivoted:
                        pivoted[t_val] = {time_col: t_val}
                    pivoted[t_val][grp_val] = r[num_col]
                
                chart_data = sorted(list(pivoted.values()), key=lambda x: str(x[time_col]))
                return {
                    "chart_type": "line",
                    "title": f"{num_col.replace('_', ' ').title()} Over Time by {group_col.title()}",
                    "x_key": time_col,
                    "y_keys": distinct_groups,
                    "x_label": time_col.title(),
                    "y_label": num_col.replace('_', ' ').title(),
                    "unit": "%" if ("rate" in num_col.lower() or "ratio" in num_col.lower() or "pct" in num_col.lower()) else "",
                    "data": chart_data
                }
            else:
                # Single group or already unique
                sorted_rows = sorted(rows, key=lambda x: str(x[time_col]))
                return {
                    "chart_type": "line",
                    "title": f"{num_col.replace('_', ' ').title()} Over Time",
                    "x_key": time_col,
                    "y_keys": [num_col],
                    "x_label": time_col.title(),
                    "y_label": num_col.replace('_', ' ').title(),
                    "unit": "%" if ("rate" in num_col.lower() or "ratio" in num_col.lower() or "pct" in num_col.lower()) else "",
                    "data": sorted_rows
                }
        else:
            # Simple date + numeric (or multiple numeric columns)
            sorted_rows = sorted(rows, key=lambda x: str(x[time_col]))
            return {
                "chart_type": "line",
                "title": f"{numeric_cols[0].replace('_', ' ').title()} Trend",
                "x_key": time_col,
                "y_keys": numeric_cols,
                "x_label": time_col.title(),
                "y_label": numeric_cols[0].replace('_', ' ').title(),
                "unit": "%" if ("rate" in numeric_cols[0].lower() or "ratio" in numeric_cols[0].lower() or "pct" in numeric_cols[0].lower()) else "",
                "data": sorted_rows
            }

    # 3. Categorical + Numeric -> Bar Chart
    if categorical_cols and numeric_cols:
        cat_col = categorical_cols[0]
        num_col = numeric_cols[0]
        return {
            "chart_type": "bar",
            "title": f"{num_col.replace('_', ' ').title()} by {cat_col.title()}",
            "x_key": cat_col,
            "y_keys": [num_col],
            "x_label": cat_col.title(),
            "y_label": num_col.replace('_', ' ').title(),
            "unit": "%" if ("rate" in num_col.lower() or "ratio" in num_col.lower() or "pct" in num_col.lower()) else "",
            "data": rows[:50]  # limit bar rendering to top 50
        }

    # 4. Default: Table
    return {
        "chart_type": "table",
        "title": "Query Results",
        "columns": columns,
        "data": rows
    }


def determine_forecast_chart_spec(forecast_res: Dict[str, Any], region: str = "Australia") -> Dict[str, Any]:
    """
    Constructs a specialized chart specification for statistical projections.
    
    Design Note:
    Forecast charts differ fundamentally from observational charts:
    1. Historical data is rendered as a continuous solid line.
    2. Projected data is rendered as a dashed line to prevent visual conflation.
    3. 80% and 95% confidence intervals are passed explicitly so the frontend can
       render bounded uncertainty ranges.
    4. The mandatory disclaimer caption is attached directly to the spec.
    """
    return {
        "chart_type": "forecast",
        "title": f"Statistical Projection: Unemployment Rate in {region} (Next 12 Months)",
        "caption": "Statistical projection, not an official forecast.",
        "x_key": "date",
        "historical_key": "historical_value",
        "projected_key": "projected_mean",
        "ci_80_lower": "ci_80_lower",
        "ci_80_upper": "ci_80_upper",
        "ci_95_lower": "ci_95_lower",
        "ci_95_upper": "ci_95_upper",
        "unit": "%",
        "data": forecast_res["chart_data"],
        "method": forecast_res["method"]
    }

