"""SM-2 spaced-repetition engine (Phase 14).

Algorithm migrated from the CAPT Taxation app's proven core/sr.py
(itself documented SM-2, adapted from SuperMemo):

Ratings map to SM-2 quality scores q:
    again -> q = 0   (complete blackout)
    hard  -> q = 3   (correct but with serious difficulty)
    good  -> q = 4   (correct after hesitation)
    easy  -> q = 5   (perfect recall)

    EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)), floored at 1.3.
    If q < 3 ('again'): lapses += 1, reps = 0, interval = 1 day.
    Else:
        reps += 1
        if reps == 1: interval = 1
        elif reps == 2: interval = 6
        else: interval = round(previous_interval * EF')
        ('hard' scales by 1.2x of the previous interval instead of EF,
        so hard cards return sooner: interval = max(1, round(prev * 1.2)).)
    next_due = today + interval days.

Pure functions over state dicts; the store persists them.
"""
from __future__ import annotations

from datetime import date, timedelta

RATINGS = ("again", "hard", "good", "easy")
_QUALITY = {"again": 0, "hard": 3, "good": 4, "easy": 5}
_EASE_FLOOR = 1.3
_DEFAULT_EASE = 2.5


def next_state(prev: dict | None, rating: str,
               today: date | None = None) -> dict:
    """Compute the next SM-2 state for a card. Never mutates inputs."""
    if rating not in RATINGS:
        raise ValueError(f"rating must be one of {RATINGS}, got {rating!r}")
    today = today or date.today()
    q = _QUALITY[rating]
    ease = _DEFAULT_EASE if not prev else float(prev.get("ease") or _DEFAULT_EASE)
    reps = 0 if not prev else int(prev.get("reps") or 0)
    interval = 0 if not prev else int(prev.get("interval_days") or 0)
    lapses = 0 if not prev else int(prev.get("lapses") or 0)

    ease = ease + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    ease = max(ease, _EASE_FLOOR)

    if q < 3:  # again
        lapses += 1
        reps = 0
        interval = 1
    else:
        reps += 1
        if rating == "hard":
            interval = max(1, round(interval * 1.2)) if interval else 1
        elif reps == 1:
            interval = 1
        elif reps == 2:
            interval = 6
        else:
            interval = max(1, round(interval * ease))

    return {
        "ease": round(ease, 4),
        "interval_days": interval,
        "reps": reps,
        "lapses": lapses,
        "next_due": (today + timedelta(days=interval)).isoformat(),
        "last_reviewed": today.isoformat(),
        "last_rating": rating,
    }


def is_due(review: dict | None, today: date | None = None) -> bool:
    """A card with no review row is always due (never reviewed)."""
    if not review or not review.get("next_due"):
        return True
    today = today or date.today()
    return review["next_due"] <= today.isoformat()
