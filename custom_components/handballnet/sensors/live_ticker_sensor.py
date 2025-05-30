from datetime import datetime, timezone
from typing import Any
from .base_sensor import HandballBaseSensor
from ..const import DOMAIN


class HandballLiveTickerSensor(HandballBaseSensor):
    def __init__(self, hass, entry, team_id):
        super().__init__(hass, entry, team_id)
        
        # Use team name from config if available, fallback to team_id
        team_name = entry.data.get("team_name", team_id)
        self._attr_name = f"Liveticker {team_name}"
        self._attr_unique_id = f"handball_live_ticker_{team_id}"
        self._attr_icon = "mdi:clock-alert"
        self._attr_should_poll = False
        self._attr_native_value = "off"

    def update_state(self) -> None:
        now_ts = datetime.now(timezone.utc).timestamp()
        matches = self.hass.data.get(DOMAIN, {}).get(self._team_id, {}).get("matches", [])
        self._attr_native_value = "on" if any(
            match.get("startsAt", 0) / 1000 <= now_ts <= match.get("startsAt", 0) / 1000 + 7200
            for match in matches
        ) else "off"

    @property
    def state(self) -> str:
        return self._attr_native_value

    @property
    def is_on(self) -> bool:
        return self._attr_native_value == "on"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "team_id": self._team_id,
            "matches_tracked": len(self.hass.data.get(DOMAIN, {}).get(self._team_id, {}).get("matches", []))
        }
