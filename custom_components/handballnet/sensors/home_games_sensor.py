from datetime import datetime, timezone
from typing import Any
from .base_sensor import HandballBaseSensor
from ..const import DOMAIN


class HandballHeimspielSensor(HandballBaseSensor):
    def __init__(self, hass, entry, team_id):
        super().__init__(hass, entry, team_id)
        self._attr_name = f"Handball Heimspiele {team_id}"
        self._attr_unique_id = f"handball_home_games_{team_id}"

    @property
    def state(self) -> int:
        return len(self.hass.data[DOMAIN][self._team_id].get("heimspiele", []))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        heimspiele = self.hass.data[DOMAIN][self._team_id].get("heimspiele", [])
        next_home_match = None
        now = datetime.now(timezone.utc)
        
        for match in sorted(heimspiele, key=lambda x: x.get("startsAt", 0)):
            match_time = datetime.fromtimestamp(match.get("startsAt", 0) / 1000, tz=timezone.utc)
            if match_time > now:
                next_home_match = {
                    "opponent": match.get("awayTeam", {}).get("name"),
                    "starts_at": match.get("startsAt"),
                    "starts_at_formatted": match_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "starts_at_local": match_time.astimezone().strftime("%Y-%m-%d %H:%M:%S"),
                    "field": match.get("field", {}).get("name")
                }
                break
        
        return {
            "total_home_games": len(heimspiele),
            "next_home_match": next_home_match
        }
