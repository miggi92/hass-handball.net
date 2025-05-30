from typing import Any
from .base_sensor import HandballBaseSensor
from ...const import DOMAIN
from ...api import HandballNetAPI
import logging

_LOGGER = logging.getLogger(__name__)

class HandballTablePositionSensor(HandballBaseSensor):
    def __init__(self, hass, entry, team_id, api: HandballNetAPI):
        super().__init__(hass, entry, team_id)
        self._api = api
        self._team_id = team_id  # Explicitly set _team_id
        self._state = None
        self._attributes = {}

        # Use team name from config if available, fallback to team_id
        team_name = entry.data.get("team_name", team_id)
        self._attr_name = f"{team_name} Tabellenplatz"
        self._attr_unique_id = f"handball_team_{team_id}_table_position"
        self._attr_icon = "mdi:format-list-numbered"

    @property
    def state(self) -> int | None:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attributes

    async def async_update(self) -> None:
        try:
            # First get team info to find the tournament ID
            team_info = await self._api.get_team_info(self._team_id)
            if not team_info:
                _LOGGER.warning("Could not get team info for %s", self._team_id)
                self._state = None
                self._attributes = {}
                return
            
            # Try to extract tournament ID from team info
            tournament_id = team_info.get("tournament", {}).get("id")
            if not tournament_id:
                _LOGGER.warning("No tournament ID found for team %s", self._team_id)
                self._state = None
                self._attributes = {}
                return
            
            # Get table position using the tournament ID
            table_position = await self._api.get_team_table_position(self._team_id, tournament_id)
            if not table_position:
                self._state = None
                self._attributes = {}
                return

            self._state = table_position.get("position")
            self._attributes = {
                "team_name": table_position.get("team_name"),
                "points": table_position.get("points"),
                "games_played": table_position.get("games_played"),
                "wins": table_position.get("wins"),
                "draws": table_position.get("draws"),
                "losses": table_position.get("losses"),
                "goals_scored": table_position.get("goals_scored"),
                "goals_conceded": table_position.get("goals_conceded"),
                "goal_difference": table_position.get("goal_difference"),
            }

        except Exception as e:
            _LOGGER.error("Error updating table position for %s: %s", self._team_id, e)
            self._state = None
            self._attributes = {"error": str(e)}