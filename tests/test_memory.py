"""Tests for engine.memory — MemoryEngine, phi scoring."""

from engine.memory import (
    MemoryEngine,
    get_memory,
    phi_recency_score,
    phi_relevance,
)


class TestPhiRecencyScore:
    def test_current_scores_high(self):
        # age_seconds=0 means "just now"
        score = phi_recency_score(0)
        assert score > 0.9

    def test_old_scores_lower(self):
        score = phi_recency_score(86400 * 30)  # 30 days old
        assert score < 0.5

    def test_score_bounded(self):
        score = phi_recency_score(86400 * 365)
        assert 0.0 <= score <= 1.0


class TestPhiRelevance:
    def test_high_inputs_high_relevance(self):
        # phi_relevance(recency, quality, frequency) -> float
        score = phi_relevance(1.0, 1.0, 1.0)
        assert score > 0.5

    def test_low_inputs_low_relevance(self):
        score = phi_relevance(0.0, 0.0, 0.0)
        assert score < 0.1


class TestMemoryEngine:
    def test_get_memory_returns_engine(self):
        mem = get_memory()
        assert isinstance(mem, MemoryEngine)

    def test_session_lifecycle(self):
        mem = get_memory()
        sid = mem.begin_session(notes="test session")
        assert sid is not None
        mem.end_session(notes="done")

    def test_log_event(self):
        mem = get_memory()
        mem.begin_session(notes="test log")
        mem.log_event(
            module="test",
            action="test_action",
            params={"key": "value"},
            result_summary="ok",
        )
        mem.end_session(notes="done")
