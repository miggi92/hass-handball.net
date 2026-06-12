from typing import Any
from .base_sensor import HandballBaseSensor


class HandballLiveTickerSensor(HandballBaseSensor):
    def __init__(self, coordinator, entry, team_id, team_name):
        super().__init__(coordinator, entry, team_id, team_name)
        self._team_id = team_id

        display_name = self._resolve_display_name(team_name)
        self._attr_name = f"{display_name} Live-Ticker"
        self._attr_unique_id = self._build_unique_id("live_ticker")
        self._attr_icon = "mdi:handball"

    @property
    def state(self) -> str | None:
        live_matches = self._get_team_bucket().get("live_matches", [])
        return "Live" if live_matches else "Kein Live-Spiel"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        live_matches = self._get_team_bucket().get("live_matches", [])
        if not live_matches:
            return {}

        return {
            "live_matches": live_matches,
            "total_live_matches": len(live_matches),
        }
