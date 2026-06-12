from datetime import datetime, timezone
from typing import Any
from .base_sensor import HandballBaseSensor
from ...const import DOMAIN

class HandballLiveTickerSensor(HandballBaseSensor):
    def __init__(self, hass, entry, team_id, team_name):
        super().__init__(hass, entry, team_id, team_name)
        self._team_id = team_id
        self._state = None
        self._attributes = {}

        club_name = entry.data.get("club_name")
        display_name = f"{club_name} {team_name}" if club_name else team_name
        self._attr_name = f"{display_name} Live-Ticker"
        self._attr_unique_id = self._build_unique_id("live_ticker")
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