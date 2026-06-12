from typing import Any
from .base_sensor import HandballBaseSensor

class HandballLiveTickerEventsSensor(HandballBaseSensor):
    def __init__(self, coordinator, entry, team_id, team_name, api=None):
        super().__init__(coordinator, entry, team_id, team_name)
        self._team_id = team_id

        display_name = self._resolve_display_name(team_name)
        self._attr_name = f"{display_name} Live Events"
        self._attr_unique_id = self._build_unique_id("live_events")
        self._attr_icon = "mdi:alert-circle-outline"

    @property
    def state(self) -> str | None:
        live_events = self._get_team_bucket().get("live_events", {})
        total_events = live_events.get("total_events", 0)
        return f"{total_events} Ereignisse" if total_events else "Keine Live-Spiele"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        live_events = self._get_team_bucket().get("live_events", {})
        if not live_events:
            return {}

        return live_events