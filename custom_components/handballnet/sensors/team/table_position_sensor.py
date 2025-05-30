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
            # Try multiple approaches to get tournament ID
            tournament_id = await self._find_tournament_id()
            
            if not tournament_id:
                self._state = "Kein Turnier gefunden"
                self._attributes = {"info": "Team ist derzeit nicht in einer aktiven Liga oder Turnier-ID konnte nicht ermittelt werden"}
                return
            
            # Get table position using the tournament ID
            table_position = await self._api.get_team_table_position(self._team_id, tournament_id)
            if not table_position:
                self._state = "Nicht in Tabelle"
                self._attributes = {
                    "info": "Team nicht in der Tabelle gefunden",
                    "tournament_id": tournament_id
                }
                return

            self._state = table_position.get("position")
            self._attributes = {
                "tournament_id": tournament_id,
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
            self._state = "Fehler"
            self._attributes = {"error": str(e)}

    async def _find_tournament_id(self) -> str | None:
        """Try different methods to find the tournament ID"""
        
        # Method 1: Get from team info
        try:
            team_info = await self._api.get_team_info(self._team_id)
            if team_info:
                tournament_id = team_info.get("tournament", {}).get("id")
                if tournament_id:
                    _LOGGER.debug("Found tournament ID from team info: %s", tournament_id)
                    return tournament_id
        except Exception as e:
            _LOGGER.debug("Could not get tournament ID from team info: %s", e)

        # Method 2: Extract from match data
        try:
            matches = self.hass.data.get(DOMAIN, {}).get(self._team_id, {}).get("matches", [])
            if matches:
                # Look for tournament ID in recent matches
                for match in matches:
                    tournament_id = match.get("tournament", {}).get("id")
                    if tournament_id:
                        _LOGGER.debug("Found tournament ID from matches: %s", tournament_id)
                        return tournament_id
        except Exception as e:
            _LOGGER.debug("Could not get tournament ID from matches: %s", e)

        # Method 3: Get from team schedule if available
        try:
            schedule = await self._api.get_team_schedule(self._team_id)
            if schedule:
                for match in schedule:
                    tournament_id = match.get("tournament", {}).get("id")
                    if tournament_id:
                        _LOGGER.debug("Found tournament ID from schedule: %s", tournament_id)
                        return tournament_id
        except Exception as e:
            _LOGGER.debug("Could not get tournament ID from schedule: %s", e)

        _LOGGER.warning("No tournament ID found for team %s", self._team_id)
        return None