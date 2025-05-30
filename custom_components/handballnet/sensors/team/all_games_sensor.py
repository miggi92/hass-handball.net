from typing import Any
from ..base_sensor import HandballBaseSensor
from ...const import DOMAIN
from ...api import HandballNetAPI
from ...utils import get_next_match_info, get_last_match_info
import logging

_LOGGER = logging.getLogger(__name__)

class HandballAllGamesSensor(HandballBaseSensor):
    def __init__(self, hass, entry, team_id, api: HandballNetAPI):
        super().__init__(hass, entry, team_id)
        self._api = api
        self._state = None
        self._attributes = {}

        # Use team name from config if available, fallback to team_id
        team_name = entry.data.get("team_name", team_id)
        self._attr_name = f"{team_name} Alle Spiele"
        self._attr_unique_id = f"handball_team_{team_id}_all_games"
        self._attr_icon = "mdi:calendar"

    @property
    def state(self) -> str | None:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attributes

    async def async_update(self) -> None:
        try:
            matches = await self._api.get_team_schedule(self._team_id)
            if not matches:
                self._state = "Keine Spiele verfügbar"
                self._attributes = {}
                return

            next_match = get_next_match_info(matches)
            last_match = get_last_match_info(matches)

            self._state = f"Nächstes Spiel: {next_match['opponent']}" if next_match else "Kein nächstes Spiel"
            self._attributes = {
                "next_match": next_match,
                "last_match": last_match,
                "total_matches": len(matches),
                "matches": matches
            }

            # Store matches in hass.data for other sensors
            if DOMAIN not in self.hass.data:
                self.hass.data[DOMAIN] = {}
            if self._team_id not in self.hass.data[DOMAIN]:
                self.hass.data[DOMAIN][self._team_id] = {}
            self.hass.data[DOMAIN][self._team_id]["matches"] = matches

        except Exception as e:
            _LOGGER.error("Error updating all games sensor for %s: %s", self._team_id, e)
            self._state = "Fehler beim Laden"
            self._attributes = {"error": str(e)}