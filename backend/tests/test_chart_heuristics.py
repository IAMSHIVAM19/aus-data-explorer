"""Tests for the Chart Heuristics Engine (chart_heuristics.py)."""

import pytest
from backend.chart_heuristics import determine_chart_spec, detect_column_types


class TestColumnTypeDetection:
    """Test automatic column type inference."""

    def test_date_column_detected(self):
        cols = ["date", "value"]
        rows = [{"date": "2024-01-01", "value": 4.2}]
        types = detect_column_types(cols, rows)
        assert types["date"] == "date"

    def test_numeric_column_detected(self):
        cols = ["region", "avg_rate"]
        rows = [{"region": "NSW", "avg_rate": 3.8}]
        types = detect_column_types(cols, rows)
        assert types["avg_rate"] == "numeric"

    def test_categorical_column_detected(self):
        cols = ["region", "value"]
        rows = [{"region": "Victoria", "value": 4.2}]
        types = detect_column_types(cols, rows)
        assert types["region"] == "categorical"

    def test_year_column_detected(self):
        cols = ["year", "value"]
        rows = [{"year": 2024, "value": 4.1}]
        types = detect_column_types(cols, rows)
        assert types["year"] == "year"


class TestChartTypeSelection:
    """Test deterministic chart type selection based on data shape."""

    def test_empty_data_returns_empty(self):
        spec = determine_chart_spec(["date", "value"], [])
        assert spec["chart_type"] == "empty"

    def test_single_scalar_returns_kpi(self, sample_single_row):
        spec = determine_chart_spec(["unemployment_rate"], sample_single_row)
        assert spec["chart_type"] == "kpi"
        assert spec["kpi_value"] == 4.2

    def test_time_series_returns_line(self, sample_time_series_rows):
        cols = ["date", "unemployment_rate"]
        spec = determine_chart_spec(cols, sample_time_series_rows)
        assert spec["chart_type"] == "line"
        assert spec["x_key"] == "date"
        assert "unemployment_rate" in spec["y_keys"]

    def test_categorical_numeric_returns_bar(self, sample_ranking_rows):
        cols = ["region", "avg_unemployment_rate"]
        spec = determine_chart_spec(cols, sample_ranking_rows)
        assert spec["chart_type"] == "bar"
        assert spec["x_key"] == "region"

    def test_multi_region_time_series_returns_multiline(self, sample_multi_region_rows):
        cols = ["date", "region", "unemployment_rate"]
        spec = determine_chart_spec(cols, sample_multi_region_rows)
        assert spec["chart_type"] == "line"
        # Should have pivoted into multiple y_keys (one per region)
        assert len(spec["y_keys"]) == 2
        assert "NSW" in spec["y_keys"]
        assert "Victoria" in spec["y_keys"]

    def test_line_chart_data_sorted_chronologically(self, sample_time_series_rows):
        # Shuffle rows
        shuffled = sample_time_series_rows[::-1]
        cols = ["date", "unemployment_rate"]
        spec = determine_chart_spec(cols, shuffled)
        dates = [d["date"] for d in spec["data"]]
        assert dates == sorted(dates)

    def test_unit_detection_for_rates(self, sample_time_series_rows):
        cols = ["date", "unemployment_rate"]
        spec = determine_chart_spec(cols, sample_time_series_rows)
        assert spec.get("unit") == "%"
