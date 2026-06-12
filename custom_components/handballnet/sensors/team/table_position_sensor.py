from typing import Any
from .base_sensor import HandballBaseSensor


class HandballTablePositionSensor(HandballBaseSensor):
    def __init__(self, coordinator, entry, team_id, team_name, api=None):
        super().__init__(coordinator, entry, team_id, team_name)
        self._team_id = team_id

        display_name = self._resolve_display_name(team_name)
        self._attr_name = f"{display_name} Tabellenplatz"
        self._attr_unique_id = self._build_unique_id("table_position")
        self._attr_icon = "mdi:format-list-numbered"

    @property
    def state(self) -> int | None:
        table_position = self._get_team_bucket().get("table_position")
        return table_position.get("position") if table_position else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        table_position = self._get_team_bucket().get("table_position")
        if not table_position:
            return {}

        return {
            "tournament_id": self._get_team_bucket().get("tournament_id"),
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
