"""
SQL Validation Layer using sqlglot
Strictly enforces read-only query execution, single SELECT ASTs, table allowlists,
row limits, and injection protection via AST analysis.
"""

import logging
from typing import Optional, Set, Tuple

import sqlglot
from sqlglot import exp

logger = logging.getLogger(__name__)

# Strictly allowlisted tables and views.
ALLOWED_TABLES: Set[str] = {
    "labour_force",
    "labour_force_monthly",
    "regional_unemployment",
    "youth_labour_force",
    "youth_unemployment",
}
MAX_ROW_LIMIT = 1000


class SQLValidationError(Exception):
    """Raised when an SQL query violates security or structural constraints."""
    pass


def validate_and_sanitize_sql(sql_str: str) -> Tuple[bool, str, Optional[str]]:
    """
    Validates the given SQL string against security guardrails.
    Returns (is_valid, sanitized_sql, error_message).
    """
    cleaned_sql = sql_str.strip()
    # Strip markdown fences if present
    if cleaned_sql.startswith("```"):
        lines = cleaned_sql.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        cleaned_sql = "\n".join(lines).strip()

    if not cleaned_sql:
        return False, "", "Query cannot be empty."

    # Parse expressions
    try:
        expressions = sqlglot.parse(cleaned_sql, read="sqlite")
    except Exception as e:
        return False, "", f"SQL Syntax Error: {str(e)}"

    # Strictly disallow multi-statement queries
    if len(expressions) != 1:
        return False, "", f"Security Guardrail Violation: Only a single statement is permitted. Found {len(expressions)} statements."

    statement = expressions[0]
    if statement is None:
        return False, "", "Could not parse statement."

    # Root statement MUST be a SELECT
    if not isinstance(statement, exp.Select):
        stmt_type = type(statement).__name__
        return False, "", f"Security Guardrail Violation: Forbidden operation '{stmt_type}'. Only SELECT statements are permitted."

    # Extract CTE alias names so they don't trigger the table allowlist check
    cte_names = set()
    with_node = statement.find(exp.With)
    if with_node:
        for cte in with_node.expressions:
            if hasattr(cte, "alias") and cte.alias:
                cte_names.add(cte.alias.lower())
            elif hasattr(cte, "alias_or_name") and cte.alias_or_name:
                cte_names.add(cte.alias_or_name.lower())

    # Check all table references against allowlist
    for table in statement.find_all(exp.Table):
        tname = table.name.lower()
        if tname and tname not in ALLOWED_TABLES and tname not in cte_names:
            return False, "", (
                f"Security Guardrail Violation: Table '{table.name}' is not in the allowed schema list "
                f"({', '.join(sorted(ALLOWED_TABLES))})."
            )

    # Block dangerous functions via AST — check for PRAGMA, ATTACH etc. as statement types
    # Note: We use AST-level validation only, not naive string matching, to avoid false positives
    for func in statement.find_all(exp.Anonymous):
        func_name = func.name.lower() if hasattr(func, "name") else ""
        if func_name in {"load_extension", "fts3_tokenizer"}:
            return False, "", f"Security Guardrail Violation: Forbidden function '{func_name}' detected."

    # Enforce LIMIT
    limit_clause = statement.args.get("limit")
    if limit_clause is None:
        statement = statement.limit(MAX_ROW_LIMIT)
    else:
        try:
            limit_val = int(limit_clause.expression.name)
            if limit_val > MAX_ROW_LIMIT:
                statement.args["limit"] = exp.Limit(expression=exp.Literal.number(MAX_ROW_LIMIT))
        except (ValueError, AttributeError):
            statement.args["limit"] = exp.Limit(expression=exp.Literal.number(MAX_ROW_LIMIT))

    sanitized_sql = statement.sql(dialect="sqlite")
    return True, sanitized_sql, None
