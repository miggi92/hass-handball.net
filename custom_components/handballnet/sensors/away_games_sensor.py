from datetime import datetime, timezone
from typing import Any
from .base_sensor import HandballBaseSensor
from ..const import DOMAIN


class HandballAuswaertsspielSensor(HandballBaseSensor):
    def __init__(self, hass, entry, team_id):
        super().__init__(hass, entry, team_id)
        self._attr_name = f"Handball Auswärtsspiele {team_id}"
        self._attr_unique_id = f"handball_away_games_{team_id}"

    @property
    def state(self) -> int:
        return len(self.hass.data[DOMAIN][self._team_id].get("auswaertsspiele", []))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        auswaertsspiele = self.hass.data[DOMAIN][self._team_id].get("auswaertsspiele", [])
        next_away_match = None
        now = datetime.now(timezone.utc)
        
        for match in sorted(auswaertsspiele, key=lambda x: x.get("startsAt", 0)):
            match_time = datetime.fromtimestamp(match.get("startsAt", 0) / 1000, tz=timezone.utc)
            if match_time > now:
                next_away_match = {
                    "opponent": match.get("homeTeam", {}).get("name"),
                    "starts_at": match.get("startsAt"),
                    "field": match.get("field", {}).get("name")
                }
                break
        
        return {
            "total_away_games": len(auswaertsspiele),
            "next_away_match": next_away_match
        }
