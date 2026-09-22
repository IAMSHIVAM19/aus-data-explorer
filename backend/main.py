"""
FastAPI Application Entrypoint
Provides REST endpoints for natural language querying, dataset schema exploration,
seed questions catalogue, and system health status.
"""

import os
from typing import Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from backend.query_service import process_user_query, DB_PATH
from backend.schema_context import CANONICAL_REGIONS, CANONICAL_METRICS, get_schema_context
import sqlite3

load_dotenv()

app = FastAPI(
    title="Aus Gov Data Explorer API",
    description="Natural language analytics for ABS Labour Force statistics with grounded narration and SQL validation guardrails.",
    version="1.0.0"
)

# Enable CORS for local React/Vite development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "message": "Aus Gov Data Explorer Backend API is online.",
        "frontend_ui": "http://localhost:3000",
        "swagger_docs": "/docs",
        "health_check": "/api/health"
    }


class QueryRequest(BaseModel):
    question: str
    api_key: Optional[str] = None
    model: Optional[str] = None


SEED_QUESTIONS = [
    {
        "id": 1,
        "category": "lookup",
        "badge": "Lookup",
        "question": "What was the unemployment rate in Victoria in 2024?",
        "description": "Monthly timeline lookup for a specific state and year."
    },
    {
        "id": 2,
        "category": "trend",
        "badge": "Trend",
        "question": "How has the unemployment rate in New South Wales changed since 2020?",
        "description": "Multi-year trend analysis showing post-2020 trajectory."
    },
    {
        "id": 3,
        "category": "ranking",
        "badge": "Ranking",
        "question": "Which region had the highest unemployment rate in 2024?",
        "description": "Cross-sectional state ranking query with bar chart."
    },
    {
        "id": 4,
        "category": "comparison",
        "badge": "Comparison",
        "question": "Compare unemployment rate trends between NSW and Victoria",
        "description": "Dual-series time visualization comparing the two largest states."
    },
    {
        "id": 5,
        "category": "advanced",
        "badge": "Volatility",
        "question": "What was the biggest year-over-year change in any region?",
        "description": "Complex YoY delta calculation identifying historical swings."
    },
    {
        "id": 6,
        "category": "trend",
        "badge": "5-Year Trend",
        "question": "Show me the unemployment rate trend for Queensland over the last 5 years",
        "description": "Dynamic rolling window trend analysis."
    },
    {
        "id": 7,
        "category": "benchmark",
        "badge": "Benchmark",
        "question": "Which regions have consistently been above the national average in 2024?",
        "description": "State benchmark against Australia aggregate."
    },
    {
        "id": 8,
        "category": "aggregate",
        "badge": "Aggregate",
        "question": "What's the average unemployment rate across all regions in 2024?",
        "description": "Grouped average breakdown across all Australian regions."
    },
    {
        "id": 9,
        "category": "ambiguous",
        "badge": "Ambiguous (Refusal)",
        "question": "What is the worst region?",
        "description": "Subjective request that triggers a clarifying response rather than guessing."
    },
    {
        "id": 10,
        "category": "unanswerable",
        "badge": "Unanswerable (Causal Refusal)",
        "question": "What caused the unemployment rate to rise in New South Wales?",
        "description": "Causal query gracefully refused because dataset is observational."
    },
    {
        "id": 11,
        "category": "lookup",
        "badge": "State Lookup",
        "question": "What was the unemployment rate in Western Australia in 2023?",
        "description": "State historical lookup."
    },
    {
        "id": 12,
        "category": "comparison",
        "badge": "Comparison",
        "question": "Compare unemployment rate trends between Queensland and South Australia",
        "description": "Multi-region trend comparison."
    },
    {
        "id": 13,
        "category": "trend",
        "badge": "Long-term Trend",
        "question": "Show me the unemployment rate trend for Australia over the last 10 years",
        "description": "National 10-year macroeconomic trend."
    },
    {
        "id": 14,
        "category": "ranking",
        "badge": "Lowest",
        "question": "Which region had the lowest unemployment rate in 2024?",
        "description": "Minimum rate ranking across Australian states."
    },
    {
        "id": 15,
        "category": "unanswerable",
        "badge": "Unanswerable (Forecast)",
        "question": "What will the unemployment rate in Australia be in 2035?",
        "description": "Future forecast refused as dataset only contains recorded historical figures."
    },
    {
        "id": 16,
        "category": "out_of_scope",
        "badge": "Out of Scope",
        "question": "What is the median housing price in Sydney?",
        "description": "Off-topic query refused as dataset is strictly labour force statistics."
    },
    {
        "id": 17,
        "category": "cross_dataset",
        "badge": "Youth Comparison",
        "question": "How does youth unemployment compare to the overall rate in Australia since 2020?",
        "description": "Cross-dataset multi-table join between ABS Table 012 (youth) and Table 010 (headline)."
    },
    {
        "id": 18,
        "category": "cross_dataset",
        "badge": "Youth Gap",
        "question": "What is the gap between youth and headline unemployment in Australia over the last 5 years?",
        "description": "Calculates the dynamic percentage-point delta between youth and overall unemployment."
    },
    {
        "id": 19,
        "category": "cross_dataset",
        "badge": "Youth vs State",
        "question": "How does youth unemployment in Victoria compare to the overall rate since 2020?",
        "description": "Cross-dataset edge case: Table 12 youth cohort (Australia) juxtaposed with state-level headline rate."
    },
    {
        "id": 20,
        "category": "forecast",
        "badge": "12M Projection",
        "question": "Project unemployment in New South Wales for the next 12 months",
        "description": "Opt-in statistical projection using Holt-Winters exponential smoothing with 80% & 95% confidence intervals."
    },
    {
        "id": 21,
        "category": "forecast",
        "badge": "Projection",
        "question": "Statistical projection of Australia unemployment for the next 12 months",
        "description": "National statistical forecast with uncertainty bounds and mandatory non-official disclaimer caption."
    },
    {
        "id": 22,
        "category": "ambiguous_forecast",
        "badge": "Clarification",
        "question": "What's next for unemployment in New South Wales?",
        "description": "Ambiguous future trajectory query prompting user to choose between historical momentum and opt-in projection."
    },
    {
        "id": 23,
        "category": "reflection",
        "badge": "Self-Heal (Alias)",
        "question": "What was the unemployment rate in Vic for 2024 (test alias reflection)?",
        "description": "Deliberately triggers an initial 0-row alias mismatch ('Vic'), repaired by self-healing loop to 'Victoria'."
    },
    {
        "id": 24,
        "category": "reflection",
        "badge": "Self-Heal (Column)",
        "question": "Show jobless rate in New South Wales since 2023 (test column reflection)",
        "description": "Deliberately triggers an initial column error ('jobless_rate'), repaired to canonical metric name."
    },
    {
        "id": 25,
        "category": "reflection_failure",
        "badge": "Safe Fallback",
        "question": "Show astronomical astronaut employment count in Sydney (test reflection failure)",
        "description": "Unrepairable query demonstrating hard retry cap (2 retries) and clean fallback without infinite loop."
    }
]


@app.get("/api/health")
def health_check():
    load_dotenv(override=True)
    db_exists = os.path.exists(DB_PATH)
    total_records = 0
    date_range = {}
    if db_exists:
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            c1 = cur.execute("SELECT COUNT(*) FROM labour_force;").fetchone()[0]
            try:
                c2 = cur.execute("SELECT COUNT(*) FROM youth_labour_force;").fetchone()[0]
            except Exception:
                c2 = 0
            total_records = c1 + c2
            d_min, d_max = cur.execute("SELECT MIN(date), MAX(date) FROM labour_force;").fetchone()
            date_range = {"start": d_min, "end": d_max}
            conn.close()
        except Exception:
            pass

    return {
        "status": "online",
        "database": {
            "connected": db_exists,
            "path": DB_PATH,
            "total_observations": total_records,
            "date_range": date_range
        },
        "dataset_source": "Australian Bureau of Statistics (ABS) Labour Force Survey, Catalogue 6202.0",
        "default_model": os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free"),
        "openrouter_configured": bool(os.getenv("OPENROUTER_API_KEY"))
    }


@app.get("/api/schema")
def get_schema():
    return {
        "regions": CANONICAL_REGIONS,
        "metrics": CANONICAL_METRICS,
        "prompt_context": get_schema_context()
    }


@app.get("/api/seed-questions")
def get_seed_questions():
    return {"questions": SEED_QUESTIONS}


@app.post("/api/query")
async def execute_query(req: QueryRequest):
    if not req.question or not req.question.strip():
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")

    result = await process_user_query(
        question=req.question.strip(),
        api_key=req.api_key,
        model=req.model
    )
    return result


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
