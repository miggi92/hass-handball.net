from datetime import datetime, timezone, timedelta
from typing import Any, Optional
import logging
from homeassistant.helpers.event import async_call_later
from ..base_sensor import HandballBaseSensor
from ...const import DOMAIN, CONF_UPDATE_INTERVAL_LIVE, DEFAULT_UPDATE_INTERVAL_LIVE
from ...api import HandballNetAPI

_LOGGER = logging.getLogger(__name__)

class HandballLiveTickerEventsSensor(HandballBaseSensor):
    def __init__(self, hass, entry, team_id, api: HandballNetAPI):
        super().__init__(hass, entry, team_id)
        self._api = api
        self._team_id = team_id  # Explicitly set _team_id
        self._state = None
        self._attributes = {}
        self._update_interval = entry.options.get(
            CONF_UPDATE_INTERVAL_LIVE,
            entry.data.get(CONF_UPDATE_INTERVAL_LIVE, DEFAULT_UPDATE_INTERVAL_LIVE)
        )
        self._attr_name = f"{team_id} Live Events"
        self._attr_unique_id = f"handball_team_{team_id}_live_events"
        self._attr_icon = "mdi:alert-circle-outline"

    @property
    def state(self) -> str | None:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attributes

    async def async_update(self) -> None:
        try:
            live_events = await self._api.get_live_events(self._team_id)
            if not live_events:
                self._state = "Keine Live-Daten verfügbar"
                self._attributes = {}
                return

            self._state = f"{len(live_events)} Ereignisse"
            self._attributes = {
                "events": live_events,
                "last_update": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            _LOGGER.error("Error updating live ticker events for %s: %s", self._team_id, e)
            self._state = "Fehler beim Laden"
            self._attributes = {"error": str(e)}

    async def schedule_next_update(self):
        async_call_later(self.hass, self._update_interval, self.async_update)