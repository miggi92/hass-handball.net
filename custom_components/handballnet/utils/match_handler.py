from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from .datetime_handler import DateTimeHandler
from .url_handler import URLHandler

class MatchHandler:
    """Handler für Match-Operationen"""

    def __init__(self):
        self.datetime_handler = DateTimeHandler()
        self.url_handler = URLHandler()

    def get_next_match(self, matches: List[Dict[str, Any]], now: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        """Get information about the next upcoming match"""
        if now is None:
            now = datetime.now(timezone.utc)

        for match in sorted(matches, key=lambda x: x.get("startsAt", 0)):
            start_dt = self.datetime_handler.timestamp_to_datetime(match.get("startsAt", 0))
            if start_dt and start_dt > now:
                return self._create_match_info(match, start_dt)
        return None

    def get_last_match(self, matches: List[Dict[str, Any]], now: Optional[datetime] = None) -> Optional[Dict[str, Any]]:
        """Get information about the last played match"""
        if now is None:
            now = datetime.now(timezone.utc)

        last_match = None
        for match in matches:
            start_dt = self.datetime_handler.timestamp_to_datetime(match.get("startsAt", 0))
            if start_dt and start_dt <= now:
                last_match = self._create_match_info(match, start_dt, include_result=True)
        return last_match

    def _create_match_info(self, match: Dict[str, Any], start_dt: datetime, include_result: bool = False) -> Dict[str, Any]:
        """Create standardized match info dictionary"""
        time_formats = self.datetime_handler.format_for_display(start_dt)

        home_team = self._create_team_info(match.get("homeTeam", {}))
        away_team = self._create_team_info(match.get("awayTeam", {}))

        is_home = match.get("isHomeMatch", False)
        opponent = away_team if is_home else home_team

        match_info = {
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

        if include_result:
            match_info.update({
                "home_goals": match.get("homeGoals"),
                "away_goals": match.get("awayGoals"),
                "state": match.get("state")
            })

        return match_info

    def _create_team_info(self, team_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create standardized team info dictionary"""
        logo_url = team_data.get("logo")
        return {
            "id": team_data.get("id"),
            "name": team_data.get("name", ""),
            "logo": self.url_handler.normalize_logo_url(logo_url) if logo_url else None
        }