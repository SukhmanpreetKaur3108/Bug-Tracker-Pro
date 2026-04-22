"""
tests/test_priority.py  —  Unit Tests: C Priority Engine
==========================================================
Tests both the Python fallback and (when available) the C library.

Technique: Boundary Value Analysis (BVA) on all three inputs.

    severity      valid range: 1–4      boundaries: 0, 1, 2, 4, 5
    age_days      valid range: 0–∞      boundaries: -1, 0, 30, 365, 366
    related_count valid range: 0–∞      boundaries: -1, 0, 5, 6

Formula (for reference):
    score = (severity/4 × 40) + (min(age/30,1) × 35) + (min(related/5,1) × 25)
"""

import pytest
from modules.priority import score_bug, _python_fallback, using_c_engine


# ── Helper: expected score ────────────────────────────────────────────────────

def expected(severity, age_days, related_count):
    """Pure-Python reference computation."""
    if severity < 1 or severity > 4 or age_days < 0 or related_count < 0:
        return 0.0
    sw = severity / 4.0
    af = min(age_days / 30.0, 1.0)
    ff = min(related_count / 5.0, 1.0)
    return sw * 40.0 + af * 35.0 + ff * 25.0


# ── Python fallback tests ─────────────────────────────────────────────────────

class TestPythonFallback:
    """Tests for _python_fallback() — always runs regardless of C library."""

    # -- Known outputs --
    def test_maximum_score(self):
        """Critical + 30+ days + 5+ related → score = 100.0"""
        assert _python_fallback(4, 30, 5) == pytest.approx(100.0)

    def test_minimum_valid_score(self):
        """Low severity, just reported, no related bugs → 10.0"""
        assert _python_fallback(1, 0, 0) == pytest.approx(10.0)

    def test_example_from_proposal(self):
        """High (3), 15 days old, 2 related → 57.50 (from project proposal)."""
        assert _python_fallback(3, 15, 2) == pytest.approx(57.50)

    def test_medium_severity_no_age_no_related(self):
        assert _python_fallback(2, 0, 0) == pytest.approx(20.0)

    # -- BVA: severity boundaries --
    def test_severity_0_returns_zero(self):
        assert _python_fallback(0, 10, 2) == pytest.approx(0.0)

    def test_severity_1_valid(self):
        assert _python_fallback(1, 0, 0) == pytest.approx(10.0)

    def test_severity_4_valid(self):
        assert _python_fallback(4, 0, 0) == pytest.approx(40.0)

    def test_severity_5_returns_zero(self):
        assert _python_fallback(5, 10, 2) == pytest.approx(0.0)

    # -- BVA: age_days boundaries --
    def test_age_minus1_returns_zero(self):
        assert _python_fallback(3, -1, 0) == pytest.approx(0.0)

    def test_age_0_contributes_nothing(self):
        score = _python_fallback(2, 0, 0)
        assert score == pytest.approx(20.0)   # only severity contributes

    def test_age_30_contributes_full(self):
        """At exactly 30 days, age_factor should be 1.0 (cap reached)."""
        score_30  = _python_fallback(2, 30, 0)
        score_365 = _python_fallback(2, 365, 0)
        assert score_30 == pytest.approx(score_365)  # cap applies

    def test_age_366_same_as_30(self):
        """Age beyond 30 days does not increase the score further."""
        assert _python_fallback(2, 30, 0) == pytest.approx(_python_fallback(2, 366, 0))

    # -- BVA: related_count boundaries --
    def test_related_count_minus1_returns_zero(self):
        assert _python_fallback(3, 10, -1) == pytest.approx(0.0)

    def test_related_count_0_contributes_nothing(self):
        assert _python_fallback(2, 0, 0) == pytest.approx(20.0)

    def test_related_count_5_contributes_full(self):
        score_5 = _python_fallback(2, 0, 5)
        score_6 = _python_fallback(2, 0, 6)
        assert score_5 == pytest.approx(score_6)  # cap at 5

    # -- Equivalence classes --
    def test_all_inputs_mid_range(self):
        assert _python_fallback(2, 15, 2) == pytest.approx(expected(2, 15, 2))

    def test_score_does_not_exceed_100(self):
        assert _python_fallback(4, 9999, 9999) <= 100.0

    def test_score_non_negative_for_valid_inputs(self):
        for sev in (1, 2, 3, 4):
            for age in (0, 15, 30, 100):
                for rel in (0, 2, 5, 10):
                    assert _python_fallback(sev, age, rel) >= 0.0


# ── score_bug() — tests the public API (uses C lib or fallback) ───────────────

class TestScoreBug:
    """Tests for the public score_bug() function."""

    def test_returns_float(self):
        result = score_bug(3, 10, 2)
        assert isinstance(result, float)

    def test_matches_expected_formula(self):
        for sev in (1, 2, 3, 4):
            for age in (0, 15, 30):
                for rel in (0, 2, 5):
                    assert score_bug(sev, age, rel) == pytest.approx(expected(sev, age, rel))

    def test_invalid_severity_returns_zero(self):
        assert score_bug(0, 10, 2) == pytest.approx(0.0)
        assert score_bug(5, 10, 2) == pytest.approx(0.0)

    def test_negative_age_returns_zero(self):
        assert score_bug(3, -1, 2) == pytest.approx(0.0)

    def test_negative_related_returns_zero(self):
        assert score_bug(3, 10, -1) == pytest.approx(0.0)

    def test_c_engine_status_is_bool(self):
        assert isinstance(using_c_engine(), bool)
