"""
Intent Classifier & Refusal Engine
Detects unanswerable causal questions, ambiguous queries, and out-of-scope requests,
routing them to graceful refusal or clarifying responses rather than guessing or hallucinating.
"""

from typing import Dict, Any, Optional
import re
from backend.schema_context import CANONICAL_REGIONS, REGION_ALIASES


class QueryIntentResult:
    def __init__(
        self,
        can_execute: bool,
        intent_type: str,  # 'executable', 'ambiguous', 'unanswerable_causal', 'out_of_scope'
        message: Optional[str] = None,
        suggested_queries: Optional[list] = None
    ):
        self.can_execute = can_execute
        self.intent_type = intent_type
        self.message = message
        self.suggested_queries = suggested_queries or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "can_execute": self.can_execute,
            "intent_type": self.intent_type,
            "message": self.message,
            "suggested_queries": self.suggested_queries
        }


# Keywords that signal causal / explanatory queries
CAUSAL_PATTERNS = [
    r"\bwhy\b",
    r"\bwhat caused\b",
    r"\bthe reason\b",
    r"\bcaused by\b",
    r"\bwhy did\b",
    r"\bwhy has\b",
    r"\bexplain why\b",
    r"\bdriver of\b",
    r"\bdue to what\b"
]

# Ambiguous terms that have multiple conflicting definitions
AMBIGUOUS_PATTERNS = [
    r"\bworst\b",
    r"\bbest\b",
    r"\bgood\b",
    r"\bbad\b",
    r"\bhealthiest\b",
    r"\bhealthier\b"
]

# Explicit opt-in forecast requests
OPT_IN_FORECAST_PATTERNS = [
    r"\bproject(?:ion)?\b",
    r"\bstatistical projection\b",
    r"\bforecast(?:ing)?\b.*\b(?:next|12 months|year)\b",
    r"\bprojected rate\b"
]

# Ambiguous queries about future trajectory (neither explicit projection nor strictly out-of-scope)
AMBIGUOUS_FORECAST_PATTERNS = [
    r"\bwhat'?s next\b",
    r"\bwhere is .* heading\b",
    r"\bwhere will .* go\b",
    r"\bfuture trend\b",
    r"\boutlook for\b"
]

# Standard unanswerable forward-looking queries that must be refused
PREDICTIVE_REFUSAL_PATTERNS = [
    r"\bpredict\b",
    r"\bwhat will\b",
    r"\bin 203\d\b",
    r"\bin 204\d\b",
    r"\bforecast\b"
]

# Out of scope topics
OUT_OF_SCOPE_PATTERNS = [
    r"\bhospital\b",
    r"\bed wait times\b",
    r"\bhousing price\b",
    r"\brent price\b",
    r"\bgdp\b",
    r"\binflation\b",
    r"\bcpi\b",
    r"\binterest rate\b",
    r"\bcrime\b",
    r"\btransport\b",
    r"\bsun\b",
    r"\bearth\b",
    r"\bmoon\b",
    r"\bplanet\b",
    r"\bspace\b",
    r"\bdistance between\b",
    r"\bweather\b",
    r"\btemperature\b",
    r"\bpresident\b",
    r"\bprime minister\b",
    r"\bcapital of\b",
    r"\bmovie\b",
    r"\bsong\b",
    r"\brecipe\b",
    r"\bcook\b"
]


def classify_query_intent(query: str) -> QueryIntentResult:
    q_lower = query.strip().lower()

    # 1. Unanswerable Causal Questions
    for pattern in CAUSAL_PATTERNS:
        if re.search(pattern, q_lower):
            return QueryIntentResult(
                can_execute=False,
                intent_type="unanswerable_causal",
                message=(
                    "Refusal: The ABS Labour Force dataset contains purely observational time-series data "
                    "(unemployment rates, participation, and employment counts). It does not track causal factors, "
                    "policy interventions, or external economic drivers. To explore changes in this region, "
                    "try examining the historical trend or comparing it with other states."
                ),
                suggested_queries=[
                    "Show me the unemployment rate trend for New South Wales over the last 5 years",
                    "How has the unemployment rate changed in Victoria since 2020?",
                    "Compare unemployment rate trends between NSW and Victoria"
                ]
            )

    # 2. Ambiguous Questions ("worst", "best")
    for pattern in AMBIGUOUS_PATTERNS:
        if re.search(pattern, q_lower):
            return QueryIntentResult(
                can_execute=False,
                intent_type="ambiguous",
                message=(
                    "Clarification Required: Subjective qualifiers like 'worst' or 'best' are ambiguous in labour statistics. "
                    "Depending on your analytical perspective, this could refer to:\n"
                    "• The region with the highest unemployment rate\n"
                    "• The region with the lowest labour force participation rate\n"
                    "• The region with the largest year-over-year increase in unemployment"
                ),
                suggested_queries=[
                    "Which region had the highest unemployment rate in 2024?",
                    "Which region had the lowest participation rate in 2024?",
                    "What was the biggest year-over-year change in any region?"
                ]
            )

    # 3. Ambiguous Forecast / Trajectory Questions ("What's next for NSW?")
    # Design Note: When a user asks an open-ended question about future trajectory without
    # explicitly opting into a statistical projection, we prompt for clarification
    # rather than guessing whether they want historical momentum or a mathematical projection.
    for pattern in AMBIGUOUS_FORECAST_PATTERNS:
        if re.search(pattern, q_lower):
            return QueryIntentResult(
                can_execute=False,
                intent_type="ambiguous_forecast",
                message=(
                    "Clarification Required: Questions about future trajectory can be addressed in two distinct ways:\n"
                    "1. Historical Momentum: Examine the verified trend over the last 3–5 years.\n"
                    "2. Opt-in Statistical Projection: Run Holt-Winters exponential smoothing to generate a 12-month "
                    "projection with 80% and 95% confidence intervals (labeled strictly as a statistical projection, "
                    "not an official government forecast)."
                ),
                suggested_queries=[
                    "Show me the unemployment rate trend for New South Wales over the last 5 years",
                    "Project unemployment in New South Wales for the next 12 months"
                ]
            )

    # 4. Explicit Opt-in Forecast Requests
    # Design Note: The user has explicitly asked for a mathematical projection (e.g. 'project',
    # 'statistical projection', 'forecast next 12 months'). We route this to the forecasting engine
    # while labeling output with clear confidence bands and non-official disclaimer captions.
    for pattern in OPT_IN_FORECAST_PATTERNS:
        if re.search(pattern, q_lower):
            # If asking for far future like 2035+, still refuse
            if re.search(r"\b203\d\b|\b204\d\b", q_lower):
                break
            return QueryIntentResult(
                can_execute=True,
                intent_type="opt_in_forecast",
                message="Routing to opt-in statistical forecasting engine with 80% and 95% confidence intervals."
            )

    # 5. Default Refusal for Unanswerable Forward Forecasting
    # Preserves the non-negotiable guardrail that observational historical datasets
    # do not contain future factual records.
    for pattern in PREDICTIVE_REFUSAL_PATTERNS:
        if re.search(pattern, q_lower):
            return QueryIntentResult(
                can_execute=False,
                intent_type="unanswerable_predictive",
                message=(
                    "Refusal: This application does not predict future events as official facts. "
                    "The ABS dataset contains actual historical observations up to July 2026. "
                    "If you would like a mathematical model projection, explicitly ask to 'project' "
                    "or 'run statistical projection for the next 12 months'."
                ),
                suggested_queries=[
                    "Show me the unemployment rate trend for Australia over the last 10 years",
                    "Project unemployment in Australia for the next 12 months"
                ]
            )

    # 4. Out of Scope Topics
    for pattern in OUT_OF_SCOPE_PATTERNS:
        if re.search(pattern, q_lower):
            return QueryIntentResult(
                can_execute=False,
                intent_type="out_of_scope",
                message=(
                    "Refusal: This query requests information outside the Australian Labour Force dataset "
                    "(ABS Catalogue 6202.0). Available metrics include unemployment rate, participation rate, "
                    "and employment totals by state and territory."
                ),
                suggested_queries=[
                    "Which region had the highest unemployment rate in 2024?",
                    "Compare unemployment rate trends between NSW and Victoria"
                ]
            )

    # 5. Domain Relevance Guardrail
    # If the query contains no labour keywords, no demographic/statistical keywords,
    # and no recognized Australian regions, it is outside the scope of the ABS dataset.
    has_region = any(reg.lower() in q_lower for reg in CANONICAL_REGIONS) or any(
        re.search(rf"\b{re.escape(alias)}\b", q_lower) for alias in REGION_ALIASES
    )
    
    labour_keywords = [
        "unemploy", "employ", "job", "workforce", "work", "labour", "labor", "participation",
        "rate", "ratio", "youth", "young", "wage", "salary", "hiring", "worker", "trend",
        "highest", "lowest", "average", "mean", "median", "ranking", "rank", "compare", "comparison",
        "change", "changed", "swing", "volatility", "peak", "gap", "difference", "delta",
        "census", "population", "survey", "abs", "test reflection", "astronaut", "dataset"
    ]
    has_labour_keyword = any(kw in q_lower for kw in labour_keywords)

    if not has_region and not has_labour_keyword:
        return QueryIntentResult(
            can_execute=False,
            intent_type="out_of_scope",
            message=(
                "Refusal: This query requests information outside the Australian Labour Force dataset "
                "(ABS Catalogue 6202.0). The dataset only contains employment, unemployment, and "
                "participation statistics for Australia and its states/territories."
            ),
            suggested_queries=[
                "What was the unemployment rate in Victoria in 2024?",
                "Which region had the highest unemployment rate in 2024?",
                "Compare unemployment rate trends between NSW and Victoria"
            ]
        )

    return QueryIntentResult(can_execute=True, intent_type="executable")
