"""Tests for the Grounded Narrator (grounded_narrator.py)."""

import pytest
from backend.grounded_narrator import compute_deterministic_stats, format_deterministic_fallback


class TestDeterministicStatsComputation:
    """Test that stats are computed correctly from raw data."""

    def test_empty_rows_returns_zero_count(self):
        stats = compute_deterministic_stats(["date", "value"], [])
        assert stats["count"] == 0

    def test_basic_stats_computed(self, sample_time_series_rows):
        cols = ["date", "region", "unemployment_rate"]
        stats = compute_deterministic_stats(cols, sample_time_series_rows)
        assert stats["count"] == 5
        assert stats["min"]["value"] == 3.9
        assert stats["max"]["value"] == 4.3
        assert "average" in stats

    def test_time_series_trend_computed(self, sample_time_series_rows):
        cols = ["date", "region", "unemployment_rate"]
        stats = compute_deterministic_stats(cols, sample_time_series_rows)
        ts = stats.get("time_series")
        assert ts is not None
        assert ts["start_period"] == "2024-01-01"
        assert ts["end_period"] == "2024-05-01"
        assert ts["absolute_change"] == pytest.approx(-0.3, abs=0.01)

    def test_ranking_computed_with_categories(self, sample_ranking_rows):
        cols = ["region", "avg_unemployment_rate"]
        stats = compute_deterministic_stats(cols, sample_ranking_rows)
        ranking = stats.get("ranking")
        assert ranking is not None
        assert ranking["top"][0]["label"] == "Tasmania"
        assert ranking["bottom"][0]["label"] == "New South Wales"

    def test_single_row_stats(self, sample_single_row):
        cols = ["unemployment_rate"]
        stats = compute_deterministic_stats(cols, sample_single_row)
        assert stats["count"] == 1
        assert stats["max"]["value"] == 4.2


class TestDeterministicFallbackNarration:
    """Test the template-based fallback narration."""

    def test_empty_data_message(self):
        msg = format_deterministic_fallback("test", {"count": 0})
        assert "No records" in msg

    def test_single_value_narration(self):
        stats = {
            "count": 1,
            "metric_column": "unemployment_rate",
            "max": {"value": 4.2, "region": "Victoria", "date": "2024-01"},
        }
        msg = format_deterministic_fallback("What was unemployment in Vic?", stats)
        assert "4.2" in msg
        assert "Victoria" in msg

    def test_time_series_narration(self):
        stats = {
            "count": 12,
            "metric_column": "unemployment_rate",
            "max": {"value": 4.5, "date": "2024-03"},
            "min": {"value": 3.8, "date": "2024-11"},
            "average": 4.1,
            "time_series": {
                "start_period": "2024-01",
                "end_period": "2024-12",
                "start_value": 4.2,
                "end_value": 3.9,
                "absolute_change": -0.3,
                "percentage_change": -7.1,
            },
        }
        msg = format_deterministic_fallback("Show trend", stats)
        assert "decreased" in msg
        assert "4.2" in msg
        assert "3.9" in msg

    def test_ranking_narration(self):
        stats = {
            "count": 4,
            "metric_column": "unemployment_rate",
            "max": {"value": 5.9},
            "min": {"value": 3.8},
            "average": 4.6,
            "ranking": {
                "top": [{"label": "Tasmania", "value": 5.9, "date": None}],
                "bottom": [{"label": "NSW", "value": 3.8, "date": None}],
            },
        }
        msg = format_deterministic_fallback("Which region highest?", stats)
        assert "Tasmania" in msg
        assert "5.9" in msg
