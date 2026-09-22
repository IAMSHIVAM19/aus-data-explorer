"""
SQL Executor Module
Handles SQLite query execution with connection management, timeouts, and read-only mode.
"""

import logging
import sqlite3
import time
from typing import Any, Dict

from backend.config import settings

logger = logging.getLogger(__name__)


def execute_sqlite_query(sql: str) -> Dict[str, Any]:
    """
    Executes a validated SQL query against the ABS labour force database.
    Enforces read-only mode and busy timeout.

    Returns dict with columns, rows, elapsed_ms, and row_count.
    """
    start_time = time.time()
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row

    try:
        conn.execute("PRAGMA query_only = ON;")
        conn.execute("PRAGMA busy_timeout = 3000;")

        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description] if cur.description else []
        elapsed_ms = round((time.time() - start_time) * 1000, 2)

        dict_rows = [dict(r) for r in rows]
        logger.debug("Query executed: %d rows in %.2fms", len(dict_rows), elapsed_ms)

        return {
            "columns": columns,
            "rows": dict_rows,
            "elapsed_ms": elapsed_ms,
            "row_count": len(dict_rows),
        }
    finally:
        conn.close()
