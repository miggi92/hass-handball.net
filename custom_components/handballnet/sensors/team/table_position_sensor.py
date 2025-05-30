from typing import Any
from ..base_sensor import HandballBaseSensor
from ...const import DOMAIN
from ...api import HandballNetAPI

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
            table_data = await self._api.get_league_table(self._team_id)
            if not table_data:
                self._state = None
                self._attributes = {}
                return

            team_data = next(
                (team for team in table_data.get("rows", []) if team.get("team", {}).get("id") == self._team_id),
                None
            )
            if not team_data:
                self._state = None
                self._attributes = {}
                return

            self._state = team_data.get("rank")
            self._attributes = {
                "team_name": team_data.get("team", {}).get("name"),
                "points": team_data.get("points"),
                "games_played": team_data.get("games"),
                "wins": team_data.get("wins"),
                "draws": team_data.get("draws"),
                "losses": team_data.get("losses"),
                "goals_scored": team_data.get("goals"),
                "goals_conceded": team_data.get("goalsAgainst"),
                "goal_difference": team_data.get("goalDifference"),
            }

        except Exception as e:
            self._state = None
            self._attributes = {"error": str(e)}