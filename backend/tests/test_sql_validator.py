"""Tests for the SQL Validation Layer (sql_validator.py)."""

import pytest
from backend.sql_validator import validate_and_sanitize_sql, ALLOWED_TABLES


class TestBasicValidation:
    """Test fundamental SQL validation rules."""

    def test_empty_query_rejected(self):
        is_valid, sql, err = validate_and_sanitize_sql("")
        assert not is_valid
        assert "empty" in err.lower()

    def test_valid_select_passes(self):
        is_valid, sql, err = validate_and_sanitize_sql(
            "SELECT date, value FROM labour_force_monthly WHERE region = 'Victoria';"
        )
        assert is_valid
        assert err is None
        assert "labour_force_monthly" in sql.lower()

    def test_markdown_fences_stripped(self):
        query = "```sql\nSELECT * FROM labour_force_monthly;\n```"
        is_valid, sql, err = validate_and_sanitize_sql(query)
        assert is_valid
        assert "```" not in sql


class TestStatementTypeEnforcement:
    """Only SELECT statements are allowed."""

    def test_drop_table_blocked(self):
        is_valid, _, err = validate_and_sanitize_sql("DROP TABLE labour_force;")
        assert not is_valid
        assert "Forbidden operation" in err

    def test_delete_blocked(self):
        is_valid, _, err = validate_and_sanitize_sql(
            "DELETE FROM labour_force WHERE year = 2020;"
        )
        assert not is_valid
        assert "Forbidden operation" in err

    def test_insert_blocked(self):
        is_valid, _, err = validate_and_sanitize_sql(
            "INSERT INTO labour_force (region) VALUES ('Test');"
        )
        assert not is_valid
        assert "Forbidden operation" in err

    def test_update_blocked(self):
        is_valid, _, err = validate_and_sanitize_sql(
            "UPDATE labour_force SET value = 0 WHERE year = 2024;"
        )
        assert not is_valid
        assert "Forbidden operation" in err

    def test_multi_statement_blocked(self):
        is_valid, _, err = validate_and_sanitize_sql(
            "SELECT 1; SELECT 2;"
        )
        assert not is_valid
        assert "single statement" in err.lower()


class TestTableAllowlist:
    """Only approved tables and views can be queried."""

    def test_allowed_tables_pass(self):
        for table in ALLOWED_TABLES:
            is_valid, _, err = validate_and_sanitize_sql(
                f"SELECT * FROM {table} LIMIT 5;"
            )
            assert is_valid, f"Table {table} should be allowed but got: {err}"

    def test_unauthorized_table_blocked(self):
        is_valid, _, err = validate_and_sanitize_sql(
            "SELECT * FROM sqlite_master;"
        )
        assert not is_valid
        assert "not in the allowed schema list" in err

    def test_cte_aliases_not_blocked(self):
        """CTE aliases should not trigger the table allowlist check."""
        query = (
            "WITH nat AS ("
            "  SELECT date, value AS national_rate "
            "  FROM labour_force_monthly "
            "  WHERE metric_name = 'Unemployment rate' AND region = 'Australia'"
            ") "
            "SELECT l.region, AVG(l.value) "
            "FROM labour_force_monthly l "
            "JOIN nat ON l.date = nat.date "
            "GROUP BY l.region;"
        )
        is_valid, sql, err = validate_and_sanitize_sql(query)
        assert is_valid, f"CTE query should pass but got: {err}"


class TestRowLimitEnforcement:
    """LIMIT clause is enforced to prevent excessive data retrieval."""

    def test_missing_limit_injected(self):
        is_valid, sql, _ = validate_and_sanitize_sql(
            "SELECT * FROM labour_force_monthly;"
        )
        assert is_valid
        assert "1000" in sql

    def test_excessive_limit_capped(self):
        is_valid, sql, _ = validate_and_sanitize_sql(
            "SELECT * FROM labour_force_monthly LIMIT 50000;"
        )
        assert is_valid
        assert "50000" not in sql

    def test_reasonable_limit_preserved(self):
        is_valid, sql, _ = validate_and_sanitize_sql(
            "SELECT * FROM labour_force_monthly LIMIT 50;"
        )
        assert is_valid
        assert "50" in sql

    def test_negative_limit_sanitized(self):
        is_valid, sql, _ = validate_and_sanitize_sql(
            "SELECT * FROM labour_force_monthly LIMIT -1;"
        )
        assert is_valid
        assert "LIMIT 1000" in sql or "LIMIT -1" not in sql


class TestAdvancedSqlFeatures:
    """Test UNION support and dangerous extension functions."""

    def test_union_query_allowed(self):
        query = (
            "SELECT date, value FROM labour_force_monthly WHERE region = 'NSW' "
            "UNION ALL "
            "SELECT date, value FROM labour_force_monthly WHERE region = 'Victoria' "
            "LIMIT 50;"
        )
        is_valid, sql, err = validate_and_sanitize_sql(query)
        assert is_valid, f"UNION query should be valid, got error: {err}"

    def test_readfile_function_blocked(self):
        query = "SELECT readfile('/etc/passwd') FROM labour_force_monthly;"
        is_valid, sql, err = validate_and_sanitize_sql(query)
        assert not is_valid
        assert "Forbidden function" in err
