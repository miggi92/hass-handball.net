from datetime import datetime, timezone
from typing import Any, Optional
from .base_sensor import HandballBaseSensor
from ..const import DOMAIN
from ..utils import format_datetime_for_display


class HandballHeimspielSensor(HandballBaseSensor):
    def __init__(self, hass, entry, team_id):
        super().__init__(hass, entry, team_id)
        
        # Use team name from config if available, fallback to team_id
        team_name = entry.data.get("team_name", team_id)
        self._attr_name = f"{team_name} Heimspiele"
        self._attr_unique_id = f"handball_{team_id}_home_games"
        self._attr_icon = "mdi:home"

    @property
    def state(self) -> str:
        next_home_match = self._get_next_home_match()
        if next_home_match:
            return f"vs {next_home_match['opponent']} - {next_home_match['starts_at_local']}"
        return "Kein nächstes Heimspiel"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        heimspiele = self.hass.data[DOMAIN][self._team_id].get("heimspiele", [])
        now = datetime.now(timezone.utc)
        
        future_matches = []
        for match in sorted(heimspiele, key=lambda x: x.get("startsAt", 0)):
            match_time = datetime.fromtimestamp(match.get("startsAt", 0) / 1000, tz=timezone.utc)
            if match_time > now:
                time_formats = format_datetime_for_display(match_time)
                future_matches.append({
                    "id": match.get("id"),
                    "opponent": match.get("awayTeam", {}).get("name"),
                    "starts_at": match.get("startsAt"),
                    "starts_at_formatted": time_formats["formatted"],
                    "starts_at_local": time_formats["local"],
                    "field": match.get("field", {}).get("name")
                })
        
        attributes = {
            "total_home_games": len(heimspiele),
            "next_home_match": future_matches[0] if future_matches else None,
            "upcoming_home_matches": future_matches[:3]  # Nächste 3 Heimspiele
        }
        
        if len(future_matches) > 1:
            attributes["second_next_home_match"] = future_matches[1]
            
        return attributes

    def _get_next_home_match(self) -> Optional[dict]:
        """Get next home match info"""
        heimspiele = self.hass.data[DOMAIN][self._team_id].get("heimspiele", [])
        now = datetime.now(timezone.utc)
        
        for match in sorted(heimspiele, key=lambda x: x.get("startsAt", 0)):
            match_time = datetime.fromtimestamp(match.get("startsAt", 0) / 1000, tz=timezone.utc)
            if match_time > now:
                time_formats = format_datetime_for_display(match_time)
                return {
                    "opponent": match.get("awayTeam", {}).get("name"),
                    "starts_at_local": time_formats["local"],
                    "field": match.get("field", {}).get("name")
                }
        return None
