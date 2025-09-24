from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from .const import GAME_DURATION_HOURS, DATE_FORMAT_UTC, DATE_FORMAT_LOCAL

def timestamp_to_datetime(timestamp: int) -> Optional[datetime]:
    """Convert timestamp to UTC datetime"""
    if not isinstance(timestamp, int) or timestamp <= 0:
        return None
    try:
        return datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
    except (ValueError, OSError):
        return None

def format_datetime_for_display(dt_or_timestamp) -> Dict[str, str]:
    """Format datetime or timestamp for display in attributes"""
    # Handle both datetime objects and timestamps
    if isinstance(dt_or_timestamp, int):
        dt = timestamp_to_datetime(dt_or_timestamp)
        if not dt:
            return {"formatted": "Invalid timestamp", "local": "Invalid timestamp"}
    elif isinstance(dt_or_timestamp, datetime):
        dt = dt_or_timestamp
    else:
        return {"formatted": "Invalid input", "local": "Invalid input"}

    return {
        "formatted": dt.strftime(DATE_FORMAT_UTC),
        "local": dt.astimezone().strftime(DATE_FORMAT_LOCAL)
    }

def is_game_live(start_timestamp: int, now: Optional[datetime] = None) -> bool:
    """Check if a game is currently live"""
    if now is None:
        now = datetime.now(timezone.utc)

    start_dt = timestamp_to_datetime(start_timestamp)
    if not start_dt:
        return False

    end_dt = start_dt + timedelta(hours=GAME_DURATION_HOURS)
    return start_dt <= now <= end_dt

def get_next_match_info(matches: list, now: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
    """Get information about the next upcoming match"""
    if now is None:
        now = datetime.now(timezone.utc)

    for match in sorted(matches, key=lambda x: x.get("startsAt", 0)):
        start_dt = timestamp_to_datetime(match.get("startsAt", 0))
        if start_dt and start_dt > now:
            time_formats = format_datetime_for_display(start_dt)
            home_logo = match.get("homeTeam", {}).get("logo")
            away_logo = match.get("awayTeam", {}).get("logo")

            home_team = {
                "id": match.get("homeTeam", {}).get("id"),
                "name": match.get("homeTeam", {}).get("name", ""),
                "logo":  normalize_logo_url(home_logo) if home_logo else None
            }
            away_team = {
                "id": match.get("awayTeam", {}).get("id"),
                "name": match.get("awayTeam", {}).get("name", ""),
                "logo":  normalize_logo_url(away_logo) if away_logo else None
            }

            # Determine opponent based on whether this is a home or away match
            is_home = match.get("isHomeMatch", False)
            opponent = away_team if is_home else home_team

            return {
                "id": match.get("id"),
                "home_team": home_team,
                "away_team": away_team,
                "opponent": opponent,
                "is_home": is_home,
                "starts_at": match.get("startsAt"),
                "starts_at_formatted": time_formats["formatted"],
                "starts_at_local": time_formats["local"],
                "field": match.get("field", {}).get("name")
            }
    return None

def get_last_match_info(matches: list, now: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
    """Get information about the last played match"""
    if now is None:
        now = datetime.now(timezone.utc)

    last_match = None
    for match in matches:
        start_dt = timestamp_to_datetime(match.get("startsAt", 0))
        if start_dt and start_dt <= now:
            time_formats = format_datetime_for_display(start_dt)
            home_team = match.get("homeTeam", {}).get("name", "")
            away_team = match.get("awayTeam", {}).get("name", "")

            # Determine opponent based on whether this was a home or away match
            is_home = match.get("isHomeMatch", False)
            opponent = away_team if is_home else home_team

            last_match = {
                "id": match.get("id"),
                "home_team": home_team,
                "away_team": away_team,
                "opponent": opponent,
                "is_home": is_home,
                "starts_at": match.get("startsAt"),
                "starts_at_formatted": time_formats["formatted"],
                "starts_at_local": time_formats["local"],
                "home_goals": match.get("homeGoals"),
                "away_goals": match.get("awayGoals"),
                "state": match.get("state")
            }
    return last_match

def normalize_logo_url(logo_url: str) -> str:
    """Convert handball-net: logo URL to full HTTPS URL"""
    from .const import HANDBALL_NET_LOGO_PREFIX, HANDBALL_NET_WEB_URL

    if logo_url and logo_url.startswith(HANDBALL_NET_LOGO_PREFIX):
        return logo_url.replace(HANDBALL_NET_LOGO_PREFIX, HANDBALL_NET_WEB_URL)
    return logo_url
