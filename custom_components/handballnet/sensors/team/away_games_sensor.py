from datetime import datetime, timezone
from typing import Any, Optional
from ..base_sensor import HandballBaseSensor
from ...const import DOMAIN
from ...utils import format_datetime_for_display

class HandballAuswaertsspielSensor(HandballBaseSensor):
    def __init__(self, hass, entry, team_id):
        super().__init__(hass, entry, team_id)
        self._state = None
        self._attributes = {}
        
        # Use team name from config if available, fallback to team_id
        team_name = entry.data.get("team_name", team_id)
        self._attr_name = f"{team_name} Auswärtsspiel"
        self._attr_unique_id = f"handball_team_{team_id}_away_game"
        self._attr_icon = "mdi:handball"

    @property
    def state(self) -> Optional[str]:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attributes

    async def async_update(self) -> None:
        """Update the sensor state and attributes."""
        now_ts = datetime.now(timezone.utc).timestamp()
        matches = self.hass.data.get(DOMAIN, {}).get(self._team_id, {}).get("matches", [])
        
        # Find the next away match
        next_away_match = None
        for match in matches:
            if match.get("isAway", False) and match.get("startsAt", 0) / 1000 > now_ts:
                next_away_match = match
                break
        
        if next_away_match:
            self._state = format_datetime_for_display(next_away_match.get("startsAt"))
            self._attributes = {
                "opponent": next_away_match.get("opponent"),
                "location": next_away_match.get("location"),
                "startsAt": next_away_match.get("startsAt"),
                "competition": next_away_match.get("competition"),
                "match_id": next_away_match.get("id"),
            }
        else:
            self._state = "Kein Auswärtsspiel geplant"
            self._attributes = {}