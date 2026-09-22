"""
Rule-Based Fallback Engine
Deterministic NL->SQL generator and self-healing repair logic.
Used when OpenRouter is unavailable or as a reliable baseline.
"""

import logging
import re
from typing import Optional

from backend.schema_context import CANONICAL_REGIONS, REGION_ALIASES, METRIC_ALIASES

logger = logging.getLogger(__name__)


def rule_based_sql_generator(question: str) -> str:
    """
    Intelligent local NL->SQL generator supporting standard analytical questions
    across the ABS labour force dataset, youth unemployment joins, and reflection tests.
    """
    q = question.lower()

    # --- Deliberate Failure Triggers for Reflection Loop Testing ---
    if "test alias reflection" in q:
        return (
            "SELECT date, value AS unemployment_rate "
            "FROM labour_force_monthly "
            "WHERE metric_name = 'Unemployment rate' AND region = 'Vic' AND year = 2024 "
            "ORDER BY date ASC;"
        )

    if "test column reflection" in q:
        return (
            "SELECT date, jobless_rate "
            "FROM labour_force_monthly "
            "WHERE region = 'New South Wales' AND year >= 2023 "
            "ORDER BY date ASC;"
        )

    if "test scope reflection" in q:
        return (
            "SELECT y.date, y.youth_unemployment_rate, h.value AS headline_unemployment_rate "
            "FROM youth_unemployment y "
            "JOIN labour_force_monthly h ON y.date = h.date AND y.region = h.region "
            "WHERE y.region = 'Victoria' AND y.year >= 2022 "
            "ORDER BY y.date ASC;"
        )

    if "test reflection failure" in q:
        return "SELECT date, astronaut_count FROM astronaut_space_force WHERE region = 'Sydney';"

    # Detect region
    target_region = None
    for alias, canonical in sorted(REGION_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        if re.search(rf"\b{re.escape(alias)}\b", q):
            target_region = canonical
            break
    if not target_region:
        for reg in sorted(CANONICAL_REGIONS, key=len, reverse=True):
            if reg.lower() in q:
                target_region = reg
                break

    # Detect years
    years = re.findall(r"\b(19\d\d|20\d\d)\b", q)

    # Detect target metric
    target_metric = "Unemployment rate"
    for alias, canonical in sorted(METRIC_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        if re.search(rf"\b{re.escape(alias)}\b", q):
            target_metric = canonical
            break
    metric_col = target_metric.lower().replace(" ", "_").replace("-", "_")

    # --- Cross-Dataset Youth Unemployment Joins ---
    if "youth" in q or "young" in q:
        if "gap" in q or "difference" in q:
            start_yr = int(years[0]) if years else 2021
            return (
                "SELECT "
                "  y.date, "
                "  y.youth_unemployment_rate, "
                "  h.value AS headline_unemployment_rate, "
                "  ROUND(y.youth_unemployment_rate - h.value, 2) AS unemployment_gap "
                "FROM youth_unemployment y "
                "JOIN labour_force_monthly h ON y.date = h.date AND y.region = h.region "
                "WHERE h.metric_name = 'Unemployment rate' "
                "  AND y.region = 'Australia' "
                f"  AND y.year >= {int(start_yr)} "
                "ORDER BY y.date ASC;"
            )

        if "compare" in q or "overall" in q or "headline" in q or "rate" in q:
            start_yr = int(years[0]) if years else 2020
            if target_region and target_region != "Australia":
                col_name = f"{target_region.lower().replace(' ', '_')}_headline_rate"
                return (
                    "SELECT "
                    "  y.date, "
                    "  y.youth_unemployment_rate AS national_youth_rate, "
                    f"  h.value AS {col_name} "
                    "FROM youth_unemployment y "
                    "JOIN labour_force_monthly h ON y.date = h.date "
                    f"WHERE h.metric_name = 'Unemployment rate' AND h.region = '{target_region}' AND y.year >= {int(start_yr)} "
                    "ORDER BY y.date ASC;"
                )
            else:
                return (
                    "SELECT "
                    "  y.date, "
                    "  y.youth_unemployment_rate, "
                    "  h.value AS headline_unemployment_rate "
                    "FROM youth_unemployment y "
                    "JOIN labour_force_monthly h ON y.date = h.date AND y.region = h.region "
                    f"WHERE h.metric_name = 'Unemployment rate' AND y.region = 'Australia' AND y.year >= {int(start_yr)} "
                    "ORDER BY y.date ASC;"
                )

        start_yr = int(years[0]) if years else 2020
        return (
            "SELECT date, youth_unemployment_rate "
            "FROM youth_unemployment "
            f"WHERE year >= {int(start_yr)} "
            "ORDER BY date ASC;"
        )

    # Compare unemployment rate trends between regions
    if "compare" in q:
        found_regions = []
        for alias, canonical in sorted(REGION_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
            if re.search(rf"\b{re.escape(alias)}\b", q) and canonical not in found_regions:
                found_regions.append(canonical)
        for reg in sorted(CANONICAL_REGIONS, key=len, reverse=True):
            if reg.lower() in q and reg not in found_regions:
                found_regions.append(reg)

        if len(found_regions) >= 2:
            reg_list = ", ".join(f"'{r}'" for r in found_regions[:2])
            year_filter = f"AND year >= {int(years[0])}" if years else "AND year >= 2018"
            return (
                f"SELECT date, region, value AS unemployment_rate "
                f"FROM labour_force_monthly "
                f"WHERE metric_name = 'Unemployment rate' "
                f"AND region IN ({reg_list}) "
                f"{year_filter} "
                f"ORDER BY date ASC;"
            )

    # Biggest year-over-year change
    if "biggest" in q and ("change" in q or "increase" in q or "swing" in q):
        return (
            "WITH yearly_avg AS ("
            "  SELECT region, year, AVG(value) AS avg_rate "
            "  FROM labour_force_monthly "
            "  WHERE metric_name = 'Unemployment rate' AND region != 'Australia' "
            "  GROUP BY region, year"
            "), "
            "yoy AS ("
            "  SELECT "
            "    curr.region, "
            "    curr.year, "
            "    ROUND(curr.avg_rate - prev.avg_rate, 2) AS yoy_change, "
            "    ROUND(curr.avg_rate, 2) AS rate "
            "  FROM yearly_avg curr "
            "  JOIN yearly_avg prev ON curr.region = prev.region AND curr.year = prev.year + 1"
            ") "
            "SELECT region, year, yoy_change "
            "FROM yoy "
            "ORDER BY ABS(yoy_change) DESC "
            "LIMIT 10;"
        )

    # Regions above national average
    if "above" in q and ("national" in q or "average" in q):
        target_year = int(years[0]) if years else 2024
        return (
            f"WITH nat AS ("
            f"  SELECT date, value AS national_rate "
            f"  FROM labour_force_monthly "
            f"  WHERE metric_name = 'Unemployment rate' AND region = 'Australia' AND year = {int(target_year)}"
            ") "
            f"SELECT l.region, ROUND(AVG(l.value), 2) AS avg_regional_rate, ROUND(AVG(nat.national_rate), 2) AS avg_national_rate "
            f"FROM labour_force_monthly l "
            f"JOIN nat ON l.date = nat.date "
            f"WHERE l.metric_name = 'Unemployment rate' AND l.region != 'Australia' AND l.year = {int(target_year)} "
            f"GROUP BY l.region "
            f"HAVING AVG(l.value) > AVG(nat.national_rate) "
            f"ORDER BY avg_regional_rate DESC;"
        )

    # Highest unemployment rate
    if ("highest" in q or "peak" in q or "max" in q) and "unemployment" in q:
        target_year = int(years[0]) if years else 2024
        return (
            f"SELECT region, ROUND(AVG(value), 2) AS avg_unemployment_rate "
            f"FROM labour_force_monthly "
            f"WHERE year = {int(target_year)} AND region != 'Australia' AND metric_name = 'Unemployment rate' "
            f"GROUP BY region "
            f"ORDER BY avg_unemployment_rate DESC "
            f"LIMIT 10;"
        )

    # Lowest unemployment rate
    if ("lowest" in q or "minimum" in q) and "unemployment" in q:
        target_year = int(years[0]) if years else 2024
        return (
            f"SELECT region, ROUND(AVG(value), 2) AS avg_unemployment_rate "
            f"FROM labour_force_monthly "
            f"WHERE year = {int(target_year)} AND region != 'Australia' AND metric_name = 'Unemployment rate' "
            f"GROUP BY region "
            f"ORDER BY avg_unemployment_rate ASC "
            f"LIMIT 10;"
        )

    # Average across all regions
    if ("average" in q or "mean" in q) and ("across" in q or "all regions" in q):
        target_year = int(years[0]) if years else 2024
        return (
            f"SELECT region, ROUND(AVG(value), 2) AS avg_unemployment_rate "
            f"FROM labour_force_monthly "
            f"WHERE metric_name = 'Unemployment rate' AND year = {int(target_year)} "
            f"GROUP BY region "
            f"ORDER BY avg_unemployment_rate DESC;"
        )

    # Trend over last N years for region
    last_n_years = re.search(r"last\s+(\d+)\s+years", q)
    if last_n_years and target_region:
        n = int(last_n_years.group(1))
        start_year = 2026 - n
        return (
            f"SELECT date, value AS unemployment_rate "
            f"FROM labour_force_monthly "
            f"WHERE metric_name = 'Unemployment rate' "
            f"AND region = '{target_region}' "
            f"AND year >= {int(start_year)} "
            f"ORDER BY date ASC;"
        )

    # Changed since / trend
    if "changed" in q or "since" in q or "trend" in q:
        start_year = int(years[0]) if years else 2020
        reg = target_region or "Australia"
        return (
            f"SELECT date, value AS {metric_col} "
            f"FROM labour_force_monthly "
            f"WHERE metric_name = '{target_metric}' "
            f"AND region = '{reg}' "
            f"AND year >= {int(start_year)} "
            f"ORDER BY date ASC;"
        )

    # Lookup for region in year
    if target_region and years:
        return (
            f"SELECT date, value AS {metric_col} "
            f"FROM labour_force_monthly "
            f"WHERE metric_name = '{target_metric}' "
            f"AND region = '{target_region}' "
            f"AND year = {int(years[0])} "
            f"ORDER BY date ASC;"
        )

    # Default lookup for region
    if target_region:
        return (
            f"SELECT date, value AS {metric_col} "
            f"FROM labour_force_monthly "
            f"WHERE metric_name = '{target_metric}' "
            f"AND region = '{target_region}' "
            f"AND year >= 2021 "
            f"ORDER BY date ASC;"
        )

    # Fallback to recent Australia headline trend
    return (
        f"SELECT date, region, value AS {metric_col} "
        f"FROM labour_force_monthly "
        f"WHERE metric_name = '{target_metric}' AND region = 'Australia' AND year >= 2021 "
        f"ORDER BY date ASC;"
    )


def rule_based_reflection_repair(
    question: str,
    failed_sql: str,
    error_message: str,
) -> str:
    """
    Deterministic self-healing repair rules for common SQL mistakes.

    Design Note:
    Do NOT fall back to a default query if the repair cannot resolve the issue.
    Silently papering over a bad query with an unrelated default result creates
    a deceptive illusion of success.
    """
    corrected = failed_sql

    # If the query references completely invalid tables, do not fabricate an answer
    if "astronaut_space_force" in failed_sql or "not in the allowed schema list" in error_message.lower():
        return failed_sql

    # Repair 1: Non-canonical state abbreviations (e.g. region = 'Vic')
    for alias, canonical in REGION_ALIASES.items():
        pattern = rf"region\s*=\s*['\"]{{1}}{re.escape(alias)}['\"]{{1}}"
        if re.search(pattern, corrected, re.IGNORECASE):
            corrected = re.sub(pattern, f"region = '{canonical}'", corrected, flags=re.IGNORECASE)
            logger.info("Reflection repair: alias '%s' -> '%s'", alias, canonical)

    # Repair 2: Column error 'no such column' or 'jobless_rate'
    if "no such column" in error_message.lower() or "jobless_rate" in corrected:
        corrected = re.sub(r"\bjobless_rate\b", "value AS unemployment_rate", corrected)
        if "metric_name" not in corrected and "labour_force" in corrected:
            corrected = corrected.replace("WHERE ", "WHERE metric_name = 'Unemployment rate' AND ")
        logger.info("Reflection repair: fixed column reference")

    # Repair 3: Youth region scope mismatch (Table 12 is national only)
    if "youth_unemployment" in corrected and re.search(r"y\.region\s*=\s*['\"](?!Australia)[^'\"]+['\"]", corrected):
        corrected = re.sub(r"y\.region\s*=\s*['\"][^'\"]+['\"]", "y.region = 'Australia'", corrected)
        logger.info("Reflection repair: youth scope corrected to Australia")

    return corrected
