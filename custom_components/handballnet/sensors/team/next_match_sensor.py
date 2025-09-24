from datetime import datetime, timezone
from typing import Any, Optional
from .base_sensor import HandballBaseSensor
from ...const import DOMAIN
from ...api import HandballNetAPI
from ...utils import HandballNetUtils
import logging

_LOGGER = logging.getLogger(__name__)

class HandballNextMatchSensor(HandballBaseSensor):
    def __init__(self, hass, entry, team_id, api: HandballNetAPI):
        super().__init__(hass, entry, team_id)
        self.utils = HandballNetUtils()
        self._api = api
        self._team_id = team_id  # Explicitly set _team_id
        self._state = None
        self._attributes = {}

        # Use team name from config if available, fallback to team_id
        team_name = entry.data.get("team_name", team_id)
        self._attr_name = f"{team_name} Nächstes Spiel"
        self._attr_unique_id = f"handball_team_{team_id}_next_match"
        self._attr_icon = "mdi:calendar-clock"

    @property
    def state(self) -> str | None:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attributes

    async def async_update(self) -> None:
        try:
            # Get matches from hass.data instead of calling API directly
            matches = self.hass.data.get(DOMAIN, {}).get(self._team_id, {}).get("matches", [])
            if not matches:
                self._state = "Keine Spiele gefunden"
                self._attributes = {}
                return

            next_match = self.utils.get_next_match_info(matches)
            if not next_match:
                self._state = "Kein nächstes Spiel"
                self._attributes = {}
                return
            opponent = next_match.get("opponent", {"name": "Unbekannter Gegner"})
            self._state = opponent["name"]
            self._attributes = {
                "match_date": next_match.get("starts_at_formatted"),
                "match_time": next_match.get("starts_at_local"),
                "home_team": next_match.get("home_team"),
                "away_team": next_match.get("away_team"),
                "field": next_match.get("field"),
                "starts_at": next_match.get("starts_at")
            }

        except Exception as e:
            _LOGGER.error("Error updating next match sensor for %s: %s", self._team_id, e)
            self._state = "Fehler beim Laden"
            self._attributes = {"error": str(e)}