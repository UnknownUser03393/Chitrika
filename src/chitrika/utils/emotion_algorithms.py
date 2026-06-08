"""Pure mathematical functions for emotion processing.

No database access — these operate on raw floats so they are fast and testable.
"""

from __future__ import annotations

# All eight Plutchik-inspired emotion dimensions
DIMENSIONS: tuple[str, ...] = (
    "joy",
    "sadness",
    "anger",
    "fear",
    "trust",
    "anticipation",
    "surprise",
    "disgust",
)


def clamp(value: float, low: float = -1.0, high: float = 1.0) -> float:
    """Clamp *value* to [*low*, *high*]."""
    return max(low, min(high, value))


# ---------------------------------------------------------------------------
# Decay
# ---------------------------------------------------------------------------


def apply_decay(
    emotions: dict[str, float],
    hours_elapsed: float,
    decay_rate: float = 0.15,
) -> dict[str, float]:
    """Drift all emotion values toward zero.

    Formula:  value *= (1 - decay_rate) ** hours_elapsed

    If *hours_elapsed* < 0.083 (≈ 5 minutes), no decay is applied to avoid
    unnecessary churn on very frequent ticks.

    Returns a new dict with the decayed values.
    """
    if hours_elapsed < 0.08:
        return {**emotions}

    factor = (1.0 - decay_rate) ** hours_elapsed
    return {dim: clamp(emotions.get(dim, 0.0) * factor) for dim in DIMENSIONS}


# ---------------------------------------------------------------------------
# Loneliness
# ---------------------------------------------------------------------------


def compute_loneliness(emotions: dict[str, float]) -> float:
    """Compute a loneliness score [0, 1] from the current emotion state.

    Weights:
        sadness       × 0.4
        (1 − trust)   × 0.2
        anticipation  × 0.2
        (1 − joy)     × 0.2

    Negative emotions (sadness, etc.) are clamped to [0, 1] before weighting.
    """
    score = (
        max(0.0, emotions.get("sadness", 0.0)) * 0.4
        + max(0.0, 1.0 - emotions.get("trust", 0.0)) * 0.2
        + max(0.0, emotions.get("anticipation", 0.0)) * 0.2
        + max(0.0, 1.0 - emotions.get("joy", 0.0)) * 0.2
    )
    return clamp(score, 0.0, 1.0)


# ---------------------------------------------------------------------------
# Mood classification
# ---------------------------------------------------------------------------


# Each mood is scored as a weighted sum of emotion dimensions.
# Keys: mood label, Values: dict of {dimension: weight}
MOOD_PROFILES: dict[str, dict[str, float]] = {
    "ecstatic":   {"joy": 0.6, "surprise": 0.4},
    "happy":      {"joy": 0.5, "trust": 0.3, "anticipation": 0.2},
    "calm":       {"trust": 0.4, "joy": 0.0, "anger": 0.0, "fear": 0.0},
    "lonely":     {"sadness": 0.4, "anticipation": 0.3, "trust": -0.3},
    "sad":        {"sadness": 0.6, "joy": -0.4},
    "angry":      {"anger": 0.5, "trust": -0.3, "disgust": 0.2},
    "anxious":    {"fear": 0.6, "anticipation": 0.2, "surprise": 0.2},
    "surprised":  {"surprise": 0.7, "joy": 0.3},
    "disgusted":  {"disgust": 0.7, "anger": 0.3},
    "neutral":    {},
}


def _calm_score(emotions: dict[str, float]) -> float:
    """Calm is high trust + low magnitude in all other emotions.

    This is a dynamic profile (not a fixed weight table) because 'calm'
    means *any* emotion is close to zero, regardless of which one.
    """
    trust = emotions.get("trust", 0.0)
    flatness = 0.0
    for dim in DIMENSIONS:
        if dim == "trust":
            continue
        flatness += 1.0 - abs(emotions.get(dim, 0.0))
    flatness /= len(DIMENSIONS) - 1  # average across 7 dims
    return trust * 0.4 + flatness * 0.6


def _neutral_score(emotions: dict[str, float]) -> float:
    """Neutral is the worst-case flatness across all dimensions.

    Using `min` instead of `mean` means a single strongly-activated
    dimension disqualifies neutral from winning — which is what we want.
    """
    return min(1.0 - abs(emotions.get(dim, 0.0)) for dim in DIMENSIONS)


def compute_mood(emotions: dict[str, float]) -> str:
    """Return the best-fitting mood label for the current emotion state.

    Each mood profile is scored as a weighted dot-product against the
    emotion dimensions.  'calm' and 'neutral' use dynamic scoring.
    """
    e = {dim: emotions.get(dim, 0.0) for dim in DIMENSIONS}

    scores: dict[str, float] = {}

    for mood, profile in MOOD_PROFILES.items():
        if mood == "calm":
            scores[mood] = _calm_score(e)
        elif mood == "neutral":
            scores[mood] = _neutral_score(e)
        else:
            total = 0.0
            for dim, weight in profile.items():
                # positive weight → favour high emotion; negative → favour low
                if weight >= 0:
                    total += e[dim] * weight
                else:
                    total += (1.0 - max(0.0, e[dim])) * abs(weight)
            scores[mood] = total

    return max(scores, key=scores.get)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Delta application
# ---------------------------------------------------------------------------


def apply_delta(
    emotions: dict[str, float],
    deltas: dict[str, float],
) -> dict[str, float]:
    """Apply per-dimension deltas, clamping each result to [-1, 1].

    Unknown keys in *deltas* are ignored; missing keys default to 0.0.
    """
    result = {**emotions}
    for dim in DIMENSIONS:
        delta = deltas.get(dim, 0.0)
        if delta != 0.0:
            result[dim] = clamp(result.get(dim, 0.0) + delta)
    return result


# ---------------------------------------------------------------------------
# Composite convenience
# ---------------------------------------------------------------------------


def analyse(emotions: dict[str, float], hours_elapsed: float = 0.0) -> dict:
    """Run the full emotion analysis pipeline and return a rich dict.

    Returns:
        emotions:   per-dimension current values
        mood:       label string
        loneliness: float [0, 1]
        dominant:   name of the dimension with highest absolute value
    """
    if hours_elapsed > 0:
        current = apply_decay(emotions, hours_elapsed)
    else:
        current = {**emotions}

    return {
        "emotions": current,
        "mood": compute_mood(current),
        "loneliness": compute_loneliness(current),
        "dominant": max(DIMENSIONS, key=lambda d: abs(current[d])),
    }
