"""
FastAPI Application Entrypoint
Provides REST endpoints for natural language querying, dataset schema exploration,
seed questions catalogue, and system health status.
"""

import json
import logging
import os
import sqlite3
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.config import settings
from backend.logging_config import setup_logging
from backend.llm_client import init_client, close_client
from backend.query_service import process_user_query
from backend.schema_context import CANONICAL_REGIONS, CANONICAL_METRICS, get_schema_context

logger = logging.getLogger(__name__)

# Load seed questions from JSON file
_seed_questions_path = os.path.join(os.path.dirname(__file__), "seed_questions.json")
with open(_seed_questions_path, "r") as f:
    SEED_QUESTIONS = json.load(f)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle — startup and shutdown."""
    setup_logging()
    logger.info("Starting Aus Gov Data Explorer API")
    await init_client()
    yield
    await close_client()
    logger.info("Aus Gov Data Explorer API shut down")


app = FastAPI(
    title="Aus Gov Data Explorer API",
    description="Natural language analytics for ABS Labour Force statistics with grounded narration and SQL validation guardrails.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — restricted to known frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    question: str
    api_key: Optional[str] = None
    model: Optional[str] = None


@app.get("/")
def root():
    return {
        "message": "Aus Gov Data Explorer Backend API is online.",
        "frontend_ui": "http://localhost:3000",
        "swagger_docs": "/docs",
        "health_check": "/api/health",
    }


@app.get("/api/health")
def health_check():
    db_exists = os.path.exists(settings.db_path)
    total_records = 0
    date_range = {}
    db_error = None

    if db_exists:
        try:
            conn = sqlite3.connect(settings.db_path)
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
        except Exception as e:
            db_error = str(e)
            logger.error("Health check database error: %s", e)

    return {
        "status": "online" if not db_error else "degraded",
        "database": {
            "connected": db_exists and not db_error,
            "path": settings.db_path,
            "total_observations": total_records,
            "date_range": date_range,
            "error": db_error,
        },
        "dataset_source": "Australian Bureau of Statistics (ABS) Labour Force Survey, Catalogue 6202.0",
        "default_model": settings.openrouter_model,
        "openrouter_configured": bool(settings.openrouter_api_key),
    }


@app.get("/api/schema")
def get_schema():
    return {
        "regions": CANONICAL_REGIONS,
        "metrics": CANONICAL_METRICS,
        "prompt_context": get_schema_context(),
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
        model=req.model,
    )
    return result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
