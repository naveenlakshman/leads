# utils/lead_score.py
from typing import Optional

def compute_lead_score(lead_source: Optional[str], start_timeframe: Optional[str], education_status: Optional[str], career_goal: Optional[str]) -> int:
    score = 0

    src = (lead_source or "").strip().lower()
    tf = (start_timeframe or "").strip().lower()
    edu = (education_status or "").strip().lower()
    goal = (career_goal or "").strip().lower()

    # Timeframe
    if "immediate" in tf or "today" in tf:
        score += 30
    elif "week" in tf:
        score += 20
    elif "month" in tf:
        score += 10
    elif "explor" in tf:
        score -= 10

    # Source
    if "walk" in src:
        score += 25
    if "referr" in src:
        score += 20
    if "instagram" in src or "reel" in src:
        score += 10
    if "seminar" in src or "college" in src:
        score += 10

    # Profile
    if "job" in goal:
        score += 20
    if "intern" in goal:
        score += 10
    if "working" in edu:
        score += 10
    if "puc" in edu or "degree" in edu or "bcom" in edu:
        score += 10

    # clamp
    if score < 0:
        score = 0
    if score > 100:
        score = 100
    return score