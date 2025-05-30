from typing import Any
from .base_sensor import HandballBaseSensor
from ..const import DOMAIN
from ..api import HandballNetAPI


class HandballTablePositionSensor(HandballBaseSensor):
    def __init__(self, hass, entry, team_id, api: HandballNetAPI):
        super().__init__(hass, entry, team_id)
        self._api = api
        self._state = None
        self._attributes = {}
        self._tournament_id = None
        
        # Use team name from config if available, fallback to team_id
        team_name = entry.data.get("team_name", team_id)
        self._attr_name = f"Tabellenplatz {team_name}"
        self._attr_unique_id = f"handball_table_position_{team_id}"
        self._attr_icon = "mdi:trophy"

    @property
    def state(self) -> int | None:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attributes

    async def async_update(self) -> None:
        # Get tournament ID from matches
        matches = self.hass.data.get(DOMAIN, {}).get(self._team_id, {}).get("matches", [])
        if not matches:
            return

        # Extract tournament ID from first match
        tournament_id = matches[0].get("tournament", {}).get("id")
        if not tournament_id:
            return

        self._tournament_id = tournament_id

        try:
            # Get table position
            table_position = await self._api.get_team_table_position(self._team_id, tournament_id)
            if table_position is None:
                # Set default values if no table position found
                self._state = None
                self._attributes = {
                    "tournament_id": tournament_id,
                    "tournament_name": matches[0].get("tournament", {}).get("name", ""),
                    "error": "Team not found in table or table not available"
                }
                return

            self._state = table_position["position"]
            self._attributes = {
                "tournament_id": tournament_id,
                "tournament_name": matches[0].get("tournament", {}).get("name", ""),
                "team_name": table_position["team_name"],
                "points": table_position["points"],
                "games_played": table_position["games_played"],
                "wins": table_position["wins"],
                "draws": table_position["draws"],
                "losses": table_position["losses"],
                "goals_scored": table_position["goals_scored"],
                "goals_conceded": table_position["goals_conceded"],
                "goal_difference": table_position["goal_difference"]
            }
        except Exception as e:
            # Log error and set error state
            from homeassistant.core import HomeAssistant
            import logging
            _LOGGER = logging.getLogger(__name__)
            _LOGGER.error("Error updating table position for team %s: %s", self._team_id, e)
            
            self._state = None
            self._attributes = {
                "tournament_id": tournament_id,
                "tournament_name": matches[0].get("tournament", {}).get("name", ""),
                "error": f"Error fetching table position: {str(e)}"
            }
