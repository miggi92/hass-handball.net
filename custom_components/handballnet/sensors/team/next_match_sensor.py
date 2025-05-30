from datetime import datetime, timezone
from typing import Any, Optional
from ..base_sensor import HandballBaseSensor
from ...const import DOMAIN
from ...api import HandballNetAPI
from ...utils import get_next_match_info, normalize_logo_url
import logging

_LOGGER = logging.getLogger(__name__)

class HandballNextMatchSensor(HandballBaseSensor):
    def __init__(self, hass, entry, team_id, api: HandballNetAPI):
        super().__init__(hass, entry, team_id)
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
            next_match = await get_next_match_info(self._api, self._team_id)
            if not next_match:
                self._state = "Kein Spiel gefunden"
                self._attributes = {}
                return

            self._state = next_match.get("opponent_name", "Unbekannter Gegner")
            self._attributes = {
                "match_date": next_match.get("match_date"),
                "match_time": next_match.get("match_time"),
                "location": next_match.get("location"),
                "opponent_logo": normalize_logo_url(next_match.get("opponent_logo")),
                "competition": next_match.get("competition"),
                "home_or_away": next_match.get("home_or_away"),
            }

        except Exception as e:
            _LOGGER.error("Error updating next match sensor for %s: %s", self._team_id, e)
            self._state = "Fehler beim Laden"
            self._attributes = {"error": str(e)}