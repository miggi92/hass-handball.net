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
        
        # Use team name from config if available, fallback to team_id
        team_name = entry.data.get("team_name", team_id)
        self._attr_name = f"{team_name} Live Events"
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
            # Check if there are any live matches
            now_ts = datetime.now(timezone.utc).timestamp()
            matches = self.hass.data.get(DOMAIN, {}).get(self._team_id, {}).get("matches", [])
            live_matches = [
                match for match in matches
                if match.get("startsAt", 0) / 1000 <= now_ts <= match.get("startsAt", 0) / 1000 + 7200
            ]
            
            if not live_matches:
                self._state = "Keine Live-Spiele"
                self._attributes = {}
                return

            # Get live ticker for the first live match
            live_match = live_matches[0]
            game_id = live_match.get("id")
            if game_id:
                live_ticker = await self._api.get_live_ticker(game_id)
                if live_ticker:
                    events = live_ticker.get("events", [])
                    self._state = f"{len(events)} Ereignisse"
                    self._attributes = {
                        "events": events[:10],  # Last 10 events
                        "total_events": len(events),
                        "game_id": game_id,
                        "last_update": datetime.now(timezone.utc).isoformat()
                    }
                else:
                    self._state = "Keine Live-Daten verfügbar"
                    self._attributes = {}
            else:
                self._state = "Keine Spiel-ID gefunden"
                self._attributes = {}
                
        except Exception as e:
            _LOGGER.error("Error updating live ticker events for %s: %s", self._team_id, e)
            self._state = "Fehler beim Laden"
            self._attributes = {"error": str(e)}