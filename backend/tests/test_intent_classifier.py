"""Tests for the Intent Classifier & Refusal Engine (intent_classifier.py)."""

import pytest
from backend.intent_classifier import classify_query_intent


class TestCausalRefusal:
    """Causal/explanatory questions should be refused."""

    @pytest.mark.parametrize("question", [
        "Why did unemployment rise in NSW?",
        "What caused the unemployment rate to increase in Victoria?",
        "Explain why unemployment dropped in 2023",
        "What is the reason for high unemployment in Tasmania?",
    ])
    def test_causal_questions_refused(self, question):
        result = classify_query_intent(question)
        assert not result.can_execute
        assert result.intent_type == "unanswerable_causal"
        assert result.suggested_queries


class TestAmbiguousRefusal:
    """Ambiguous subjective questions should request clarification."""

    @pytest.mark.parametrize("question", [
        "What is the worst region?",
        "Which state is the best for employment?",
        "Is unemployment good or bad in Victoria?",
    ])
    def test_ambiguous_questions_refused(self, question):
        result = classify_query_intent(question)
        assert not result.can_execute
        assert result.intent_type == "ambiguous"
        assert result.suggested_queries


class TestOutOfScope:
    """Off-topic questions outside the labour force dataset should be refused."""

    @pytest.mark.parametrize("question", [
        "What is the median housing price in Sydney?",
        "What is the GDP of Australia?",
        "Show me the inflation rate for 2024",
        "What are hospital ED wait times in Melbourne?",
    ])
    def test_out_of_scope_refused(self, question):
        result = classify_query_intent(question)
        assert not result.can_execute
        assert result.intent_type == "out_of_scope"


class TestPredictiveRefusal:
    """Future prediction requests should be refused (unless opt-in forecast)."""

    @pytest.mark.parametrize("question", [
        "What will the unemployment rate be in 2035?",
        "Predict unemployment in NSW for 2040",
    ])
    def test_predictive_questions_refused(self, question):
        result = classify_query_intent(question)
        assert not result.can_execute
        assert "unanswerable" in result.intent_type or "predictive" in result.intent_type


class TestOptInForecast:
    """Explicit opt-in forecast requests should be routed to forecasting engine."""

    @pytest.mark.parametrize("question", [
        "Project unemployment in NSW for the next 12 months",
        "Statistical projection of Australia unemployment for the next 12 months",
    ])
    def test_opt_in_forecast_allowed(self, question):
        result = classify_query_intent(question)
        assert result.can_execute
        assert result.intent_type == "opt_in_forecast"


class TestAmbiguousForecast:
    """Ambiguous trajectory questions should request clarification."""

    @pytest.mark.parametrize("question", [
        "What's next for unemployment in NSW?",
        "Where is unemployment heading in Australia?",
    ])
    def test_ambiguous_forecast_clarified(self, question):
        result = classify_query_intent(question)
        assert not result.can_execute
        assert result.intent_type == "ambiguous_forecast"


class TestExecutableQueries:
    """Standard analytical questions should pass through."""

    @pytest.mark.parametrize("question", [
        "What was the unemployment rate in Victoria in 2024?",
        "Compare unemployment rate trends between NSW and Victoria",
        "Which region had the highest unemployment rate in 2024?",
        "Show me the unemployment rate trend for Australia over the last 10 years",
        "How does youth unemployment compare to the overall rate since 2020?",
    ])
    def test_executable_queries_pass(self, question):
        result = classify_query_intent(question)
        assert result.can_execute
        assert result.intent_type in ("executable", "opt_in_forecast")
