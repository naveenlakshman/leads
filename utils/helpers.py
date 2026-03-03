# utils/helpers.py
from datetime import datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
UTC = ZoneInfo("UTC")

def utc_to_ist(dt: datetime | None) -> datetime | None:
    """DB stores naive UTC datetime; convert to aware IST for display."""
    if dt is None:
        return None
    # treat naive as UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(IST)

def parse_date(date_str: str | None):
    """Parse YYYY-MM-DD string to date object (or None)."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None