from datetime import datetime, timezone
from typing import Any, Optional
from .base_sensor import HandballBaseSensor
from ...const import DOMAIN
from ...utils import format_datetime_for_display

class HandballHeimspielSensor(HandballBaseSensor):
    def __init__(self, hass, entry, team_id):
        super().__init__(hass, entry, team_id)
        self._team_id = team_id  # Explicitly set _team_id
        self._state = None
        self._attributes = {}
        
        # Use team name from config if available, fallback to team_id
        team_name = entry.data.get("team_name", team_id)
        self._attr_name = f"{team_name} Heimspiel"
        self._attr_unique_id = f"handball_team_{team_id}_home_game"
        self._attr_icon = "mdi:home"

    @property
    def state(self) -> Optional[str]:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attributes

    async def async_update(self) -> None:
        matches = self.hass.data.get(DOMAIN, {}).get(self._team_id, {}).get("matches", [])
        now_ts = datetime.now(timezone.utc).timestamp()

        next_home_game = None
        for match in matches:
            if match.get("isHomeMatch") and match.get("startsAt", 0) / 1000 > now_ts:
                next_home_game = match
                break

        if next_home_game:
            # Get the timestamp and format it properly
            starts_at = next_home_game.get("startsAt")
            time_formats = format_datetime_for_display(starts_at)
            
            # Determine opponent team
            home_team = next_home_game.get("homeTeam", {}).get("name", "")
            away_team = next_home_game.get("awayTeam", {}).get("name", "")
            opponent = away_team if home_team else home_team  # If this is a home match, opponent is away team
            
            self._state = time_formats["formatted"]
            self._attributes = {
                "opponent": opponent,
                "home_team": home_team,
                "away_team": away_team,
                "location": next_home_game.get("field", {}).get("name", ""),
                "startsAt": starts_at,
                "starts_at_local": time_formats["local"],
            }
        else:
            self._state = "Kein Heimspiel geplant"
            self._attributes = {}