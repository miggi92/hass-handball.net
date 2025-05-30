from datetime import datetime, timezone
from typing import Any, Optional
from .base_sensor import HandballBaseSensor
from ..const import DOMAIN
from ..utils import format_datetime_for_display


class HandballAuswaertsspielSensor(HandballBaseSensor):
    def __init__(self, hass, entry, team_id):
        super().__init__(hass, entry, team_id)
        
        # Use team name from config if available, fallback to team_id
        team_name = entry.data.get("team_name", team_id)
        self._attr_name = f"Auswärtsspiele {team_name}"
        self._attr_unique_id = f"handball_away_games_{team_id}"
        self._attr_icon = "mdi:bus-side"

    @property
    def state(self) -> str:
        next_away_match = self._get_next_away_match()
        if next_away_match:
            return f"@ {next_away_match['opponent']} - {next_away_match['starts_at_local']}"
        return "Kein nächstes Auswärtsspiel"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        auswaertsspiele = self.hass.data[DOMAIN][self._team_id].get("auswaertsspiele", [])
        now = datetime.now(timezone.utc)
        
        future_matches = []
        for match in sorted(auswaertsspiele, key=lambda x: x.get("startsAt", 0)):
            match_time = datetime.fromtimestamp(match.get("startsAt", 0) / 1000, tz=timezone.utc)
            if match_time > now:
                time_formats = format_datetime_for_display(match_time)
                future_matches.append({
                    "id": match.get("id"),
                    "opponent": match.get("homeTeam", {}).get("name"),
                    "starts_at": match.get("startsAt"),
                    "starts_at_formatted": time_formats["formatted"],
                    "starts_at_local": time_formats["local"],
                    "field": match.get("field", {}).get("name")
                })
        
        attributes = {
            "total_away_games": len(auswaertsspiele),
            "next_away_match": future_matches[0] if future_matches else None,
            "upcoming_away_matches": future_matches[:3]  # Nächste 3 Auswärtsspiele
        }
        
        if len(future_matches) > 1:
            attributes["second_next_away_match"] = future_matches[1]
            
        return attributes

    def _get_next_away_match(self) -> Optional[dict]:
        """Get next away match info"""
        auswaertsspiele = self.hass.data[DOMAIN][self._team_id].get("auswaertsspiele", [])
        now = datetime.now(timezone.utc)
        
        for match in sorted(auswaertsspiele, key=lambda x: x.get("startsAt", 0)):
            match_time = datetime.fromtimestamp(match.get("startsAt", 0) / 1000, tz=timezone.utc)
            if match_time > now:
                time_formats = format_datetime_for_display(match_time)
                return {
                    "opponent": match.get("homeTeam", {}).get("name"),
                    "starts_at_local": time_formats["local"],
                    "field": match.get("field", {}).get("name")
                }
        return None
