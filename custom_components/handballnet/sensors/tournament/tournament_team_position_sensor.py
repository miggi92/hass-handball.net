from typing import Any, Dict
from .base_sensor import HandballBaseSensor
from ...utils import HandballNetUtils

class HandballTournamentTeamPositionSensor(HandballBaseSensor):
    def __init__(self, coordinator, entry, tournament_id, team_data: Dict[str, Any]):
        super().__init__(coordinator, entry, tournament_id)
        self.utils = HandballNetUtils()
        self._tournament_id = tournament_id
        self._team_id = team_data.get("team_id")
        self._position = team_data.get("position", 0)
        self._team_name = team_data.get("team_name", "")

        tournament_name = entry.data.get("tournament_name", tournament_id)

        self._attr_name = f"{tournament_name} Platz {self._position}"
        self._attr_unique_id = f"handball_tournament_{tournament_id}_position_{self._position}"
        self._attr_icon = "mdi:trophy-outline"

        team_logo = team_data.get("team_logo")
        if team_logo:
            self._attr_entity_picture = self.utils.normalize_logo_url(team_logo)

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"tournament_{tournament_id}")},
            "name": f"{tournament_name}",
            "manufacturer": "handball.net",
            "model": "Handball Tournament",
            "entry_type": "service"
        }

    @property
    def state(self) -> int | None:
        return self._get_team_data().get("position")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        team_data = self._get_team_data()
        games_played = team_data.get("games_played", 0)
        wins = team_data.get("wins", 0)
        draws = team_data.get("draws", 0)
        losses = team_data.get("losses", 0)
        goals_scored = team_data.get("goals_scored", 0)
        goals_conceded = team_data.get("goals_conceded", 0)

        return {
            "team_id": team_data.get("team_id"),
            "team_name": team_data.get("team_name"),
            "team_acronym": team_data.get("team_acronym"),
            "position": team_data.get("position"),
            "points": team_data.get("points"),
            "games_played": games_played,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_scored": goals_scored,
            "goals_conceded": goals_conceded,
            "goal_difference": team_data.get("goal_difference", 0),
            "promoted": team_data.get("promoted"),
            "relegated": team_data.get("relegated"),
            "win_percentage": round((wins / games_played) * 100, 1) if games_played > 0 else 0.0,
            "draw_percentage": round((draws / games_played) * 100, 1) if games_played > 0 else 0.0,
            "loss_percentage": round((losses / games_played) * 100, 1) if games_played > 0 else 0.0,
            "avg_goals_scored": round(goals_scored / games_played, 2) if games_played > 0 else 0.0,
            "avg_goals_conceded": round(goals_conceded / games_played, 2) if games_played > 0 else 0.0,
            "points_per_game": round(wins * 2 + draws / games_played, 2) if games_played > 0 else 0.0,
            "is_leader": team_data.get("position") == 1,
            "is_last_place": team_data.get("is_last_place", False),
            "is_promotion_zone": team_data.get("promoted", False),
            "is_relegation_zone": team_data.get("relegated", False),
        }

    @property
    def entity_picture(self):
        team_data = self._get_team_data()
        team_logo = team_data.get("team_logo")
        if team_logo:
            return self.utils.normalize_logo_url(team_logo)
        return self._attr_entity_picture

    def _get_team_data(self) -> Dict[str, Any]:
        tournament_bucket = self._get_tournament_bucket()
        team_positions = tournament_bucket.get("team_positions", {})
        if self._team_id and self._team_id in team_positions:
            return team_positions[self._team_id]

        table_rows = tournament_bucket.get("table_rows", [])
        for team_row in table_rows:
            if team_row.get("team_id") == self._team_id or team_row.get("position") == self._position:
                return team_row

        return {}
