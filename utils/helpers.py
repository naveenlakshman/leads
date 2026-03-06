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


def log_activity(user_id: int, lead_id: int, action_type: str, description: str = None, 
                 field_changed: str = None, old_value: str = None, new_value: str = None):
    """
    Log user activity for audit trail.
    
    Args:
        user_id: ID of user performing the action
        lead_id: ID of lead involved
        action_type: Type of action (lead_created, lead_edited, stage_changed, followup_added, lead_converted, lead_lost)
        description: Human-readable description of the action
        field_changed: Name of field that changed (e.g., "stage", "notes")
        old_value: Previous value of the field
        new_value: New value of the field
    """
    from models import db, Activity
    
    activity = Activity(
        user_id=user_id,
        lead_id=lead_id,
        action_type=action_type,
        description=description,
        field_changed=field_changed,
        old_value=old_value,
        new_value=new_value
    )
    
    db.session.add(activity)
    db.session.commit()