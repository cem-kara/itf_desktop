from __future__ import annotations

from datetime import date, datetime
from typing import Iterable


DB_DATE_FORMAT = "%Y-%m-%d"
KNOWN_DATE_FORMATS = (
    "%Y-%m-%d",
    "%d.%m.%Y",
    "%d/%m/%Y",
    "%Y/%m/%d",
    "%d-%m-%Y",
    "%Y.%m.%d",
)


def parse_date(value) -> date | None:
    """Parse common date representations into ``date``."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = str(value).strip()
    if not text:
        return None

    for fmt in KNOWN_DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def to_db_date(value):
    """
    Normalize a date-like value to YYYY-MM-DD.
    Returns original value if parse fails.
    """
    parsed = parse_date(value)
    if not parsed:
        return value
    return parsed.strftime(DB_DATE_FORMAT)


def to_ui_date(value, fallback=""):
    """Format a date-like value as dd.MM.yyyy for UI labels."""
    parsed = parse_date(value)
    if not parsed:
        return fallback if value is None else str(value)
    return parsed.strftime("%d.%m.%Y")


def looks_like_date_column(column_name: str) -> bool:
    """
    Detect date columns by convention:
    Tarih, Tarihi, Date, _date suffixes.
    """
    if not column_name:
        return False
    name = str(column_name).strip().lower()
    return (
        name.endswith("tarih")
        or name.endswith("tarihi")
        or name.endswith("date")
        or name.endswith("_date")
    )


def normalize_date_fields(data: dict, date_fields: Iterable[str]) -> dict:
    """Return a copy with selected fields normalized to DB date format."""
    out = dict(data or {})
    for field in date_fields or ():
        if field in out:
            out[field] = to_db_date(out.get(field))
    return out
