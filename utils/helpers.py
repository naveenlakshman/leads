# utils/helpers.py
from datetime import datetime
from typing import Optional

# zoneinfo is standard library in Python 3.9+; use backport for 3.8
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
UTC = ZoneInfo("UTC")

def utc_to_ist(dt: Optional[datetime]) -> Optional[datetime]:
    """DB stores naive UTC datetime; convert to aware IST for display."""
    if dt is None:
        return None
    # treat naive as UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(IST)

def parse_date(date_str: Optional[str]):
    """Parse YYYY-MM-DD string to date object (or None)."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return None