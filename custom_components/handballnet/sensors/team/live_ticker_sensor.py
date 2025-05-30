from datetime import datetime, timezone
from typing import Any
from ..base_sensor import HandballBaseSensor
from ...const import DOMAIN

class HandballLiveTickerSensor(HandballBaseSensor):
    def __init__(self, hass, entry, team_id):
        super().__init__(hass, entry, team_id)
        self._team_id = team_id  # Explicitly set _team_id
        self._state = None
        self._attributes = {}

        # Use team name from config if available, fallback to team_id
        team_name = entry.data.get("team_name", team_id)
        self._attr_name = f"{team_name} Live-Ticker"
        self._attr_unique_id = f"handball_team_{team_id}_live_ticker"
        self._attr_icon = "mdi:handball"

    @property
    def state(self) -> str | None:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attributes

    def update_state(self) -> None:
        """Update the sensor state based on current matches"""
        now_ts = datetime.now(timezone.utc).timestamp()
        matches = self.hass.data.get(DOMAIN, {}).get(self._team_id, {}).get("matches", [])
        live_matches = [
            match for match in matches
            if match.get("startsAt", 0) / 1000 <= now_ts <= match.get("startsAt", 0) / 1000 + 7200
        ]

        if live_matches:
            self._state = "Live"
            self._attributes = {
                "live_matches": live_matches,
                "total_live_matches": len(live_matches)
            }
        else:
            self._state = "Kein Live-Spiel"
            self._attributes = {}

    async def async_update(self) -> None:
        """Async update method"""
        self.update_state()