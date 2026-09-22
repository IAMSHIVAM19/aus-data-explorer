"""Shared test fixtures for the backend test suite."""

import pytest


@pytest.fixture
def sample_time_series_rows():
    """Sample time-series rows for testing chart heuristics and stats."""
    return [
        {"date": "2024-01-01", "region": "Victoria", "unemployment_rate": 4.2},
        {"date": "2024-02-01", "region": "Victoria", "unemployment_rate": 4.1},
        {"date": "2024-03-01", "region": "Victoria", "unemployment_rate": 4.3},
        {"date": "2024-04-01", "region": "Victoria", "unemployment_rate": 4.0},
        {"date": "2024-05-01", "region": "Victoria", "unemployment_rate": 3.9},
    ]


@pytest.fixture
def sample_ranking_rows():
    """Sample categorical ranking rows."""
    return [
        {"region": "Victoria", "avg_unemployment_rate": 4.5},
        {"region": "New South Wales", "avg_unemployment_rate": 3.8},
        {"region": "Queensland", "avg_unemployment_rate": 5.1},
        {"region": "Tasmania", "avg_unemployment_rate": 5.9},
    ]


@pytest.fixture
def sample_single_row():
    """Single scalar result."""
    return [{"unemployment_rate": 4.2}]


@pytest.fixture
def sample_multi_region_rows():
    """Multi-region time-series for pivot chart testing."""
    return [
        {"date": "2024-01-01", "region": "NSW", "unemployment_rate": 3.5},
        {"date": "2024-01-01", "region": "Victoria", "unemployment_rate": 4.2},
        {"date": "2024-02-01", "region": "NSW", "unemployment_rate": 3.6},
        {"date": "2024-02-01", "region": "Victoria", "unemployment_rate": 4.1},
    ]
