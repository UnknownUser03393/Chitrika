"""Datetime helpers — consistent UTC handling for SQLite (naive storage)."""

from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Return the current time as a naive UTC datetime.

    SQLite does not store timezone information.  To keep arithmetic
    consistent, we use naive UTC everywhere.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def ensure_naive(dt: datetime) -> datetime:
    """Return *dt* as a naive datetime (strip tzinfo if present)."""
    if dt.tzinfo is not None:
        return dt.replace(tzinfo=None)
    return dt


def hours_between(later: datetime, earlier: datetime) -> float:
    """Return the number of hours between two (possibly naive) datetimes."""
    return (ensure_naive(later) - ensure_naive(earlier)).total_seconds() / 3600.0


def days_between(later: datetime, earlier: datetime) -> int:
    """Return the number of days between two (possibly naive) datetimes."""
    return (ensure_naive(later) - ensure_naive(earlier)).days
