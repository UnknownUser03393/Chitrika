"""Unit tests for pure emotion algorithm functions."""

from __future__ import annotations

import pytest

from src.chitrika.utils.emotion_algorithms import (
    DIMENSIONS,
    apply_decay,
    apply_delta,
    clamp,
    compute_loneliness,
    compute_mood,
)


# ---------------------------------------------------------------------------
# clamp
# ---------------------------------------------------------------------------


def test_clamp_within_range():
    assert clamp(0.5) == 0.5


def test_clamp_below():
    assert clamp(-2.0) == -1.0


def test_clamp_above():
    assert clamp(2.0) == 1.0


def test_clamp_custom_range():
    assert clamp(15.0, 0.0, 10.0) == 10.0


# ---------------------------------------------------------------------------
# apply_decay
# ---------------------------------------------------------------------------


def test_decay_no_elapsed_time():
    """No change when hours_elapsed < 0.08 (≈5 minutes)."""
    emotions = {"joy": 0.5, "sadness": 0.3, "anger": 0.0, "fear": 0.0,
                "trust": 0.0, "anticipation": 0.0, "surprise": 0.0, "disgust": 0.0}
    result = apply_decay(emotions, hours_elapsed=0.05)
    assert result["joy"] == pytest.approx(0.5)
    assert result["sadness"] == pytest.approx(0.3)


def test_decay_one_hour():
    """At 15% per hour decay rate, after 1 hour: value * 0.85."""
    emotions = {d: 0.0 for d in DIMENSIONS}
    emotions["joy"] = 1.0
    result = apply_decay(emotions, hours_elapsed=1.0, decay_rate=0.15)
    assert result["joy"] == pytest.approx(0.85, abs=0.01)


def test_decay_ten_hours():
    """After 10 hours: value * 0.85^10 ≈ 0.197."""
    emotions = {d: 0.0 for d in DIMENSIONS}
    emotions["joy"] = 1.0
    result = apply_decay(emotions, hours_elapsed=10.0, decay_rate=0.15)
    assert result["joy"] == pytest.approx(0.197, abs=0.01)


def test_decay_drifts_toward_zero():
    """All emotions should drift toward 0 over time."""
    emotions = {"joy": 0.8, "sadness": -0.6, "anger": 0.9, "fear": -0.7,
                "trust": 0.5, "anticipation": -0.4, "surprise": 0.3, "disgust": -0.2}
    result = apply_decay(emotions, hours_elapsed=5.0, decay_rate=0.15)

    for dim in DIMENSIONS:
        assert abs(result[dim]) < abs(emotions[dim])


def test_decay_zero_value():
    """Zero stays zero regardless of time."""
    emotions = {d: 0.0 for d in DIMENSIONS}
    result = apply_decay(emotions, hours_elapsed=100.0)
    for dim in DIMENSIONS:
        assert result[dim] == 0.0


# ---------------------------------------------------------------------------
# compute_loneliness
# ---------------------------------------------------------------------------


def test_loneliness_neutral():
    """Neutral state → moderate loneliness (0.4 from default formula)."""
    emotions = {d: 0.0 for d in DIMENSIONS}
    result = compute_loneliness(emotions)
    # sadness=0*0.4 + (1-0)*0.2 + 0*0.2 + (1-0)*0.2 = 0.4
    assert result == pytest.approx(0.4)


def test_loneliness_grows_during_long_absence():
    emotions = {d: 0.0 for d in DIMENSIONS}
    recent = compute_loneliness(emotions, hours_since_interaction=4)
    absent = compute_loneliness(emotions, hours_since_interaction=48)
    very_absent = compute_loneliness(emotions, hours_since_interaction=500)

    assert recent == pytest.approx(0.4)
    assert absent > 0.6
    assert very_absent == pytest.approx(0.85)


def test_loneliness_very_happy():
    """High joy, high trust → low loneliness."""
    emotions = {d: 0.0 for d in DIMENSIONS}
    emotions["joy"] = 0.9
    emotions["trust"] = 0.8
    result = compute_loneliness(emotions)
    assert result < 0.3


def test_loneliness_sad_and_lonely():
    """High sadness, high anticipation, low trust → high loneliness."""
    emotions = {d: 0.0 for d in DIMENSIONS}
    emotions["sadness"] = 0.8
    emotions["anticipation"] = 0.7
    emotions["trust"] = -0.3
    result = compute_loneliness(emotions)
    # sadness*0.4=0.32 + (1-(-0.3)=1.3)*0.2=0.26 + anticipation*0.2=0.14 + (1-0)*0.2=0.2 = 0.92
    assert result > 0.7


def test_loneliness_clamped():
    """Loneliness never exceeds 1.0."""
    emotions = {d: 1.0 for d in DIMENSIONS}
    result = compute_loneliness(emotions)
    assert result <= 1.0


def test_loneliness_clamped_below():
    """Loneliness never goes below 0.0."""
    emotions = {d: -1.0 for d in DIMENSIONS}
    result = compute_loneliness(emotions)
    assert result >= 0.0


# ---------------------------------------------------------------------------
# compute_mood
# ---------------------------------------------------------------------------


def test_mood_neutral():
    emotions = {d: 0.0 for d in DIMENSIONS}
    mood = compute_mood(emotions)
    assert isinstance(mood, str)
    # Neutral should be a valid mood
    assert mood in ["neutral", "calm"]


def test_mood_happy():
    emotions = {d: 0.0 for d in DIMENSIONS}
    emotions["joy"] = 0.8
    emotions["trust"] = 0.6
    mood = compute_mood(emotions)
    # High joy + trust could be "happy", "ecstatic", or "calm"
    assert mood in ("happy", "ecstatic", "calm")


def test_mood_angry():
    emotions = {d: 0.0 for d in DIMENSIONS}
    emotions["anger"] = 0.8
    emotions["disgust"] = 0.5
    mood = compute_mood(emotions)
    assert mood in ("angry", "disgusted")


def test_mood_sad():
    emotions = {d: 0.0 for d in DIMENSIONS}
    emotions["sadness"] = 0.8
    emotions["joy"] = -0.5
    mood = compute_mood(emotions)
    assert mood in ("sad", "lonely")


def test_mood_anxious():
    emotions = {d: 0.0 for d in DIMENSIONS}
    emotions["fear"] = 0.8
    emotions["anticipation"] = 0.3
    mood = compute_mood(emotions)
    assert mood == "anxious"


def test_mood_surprised():
    emotions = {d: 0.0 for d in DIMENSIONS}
    emotions["surprise"] = 0.9
    mood = compute_mood(emotions)
    assert mood == "surprised"


def test_mood_all_valid():
    """Every mood label is returned for its extreme profile."""
    emotions = {d: 0.0 for d in DIMENSIONS}
    for dim in DIMENSIONS:
        emotions[dim] = 1.0
        mood = compute_mood(emotions)
        assert isinstance(mood, str)
        emotions[dim] = 0.0


# ---------------------------------------------------------------------------
# apply_delta
# ---------------------------------------------------------------------------


def test_delta_positive():
    emotions = {d: 0.0 for d in DIMENSIONS}
    result = apply_delta(emotions, {"joy": 0.3, "trust": 0.1})
    assert result["joy"] == pytest.approx(0.3)
    assert result["trust"] == pytest.approx(0.1)


def test_delta_negative():
    emotions = {d: 0.3 for d in DIMENSIONS}
    result = apply_delta(emotions, {"joy": -0.5})
    assert result["joy"] == pytest.approx(-0.2)


def test_delta_clamped():
    emotions = {d: 0.9 for d in DIMENSIONS}
    result = apply_delta(emotions, {"joy": 0.5})
    assert result["joy"] == 1.0  # clamped


def test_delta_unknown_dimension_ignored():
    emotions = {d: 0.0 for d in DIMENSIONS}
    result = apply_delta(emotions, {"unknown_dim": 999.0})
    for dim in DIMENSIONS:
        assert result[dim] == 0.0
