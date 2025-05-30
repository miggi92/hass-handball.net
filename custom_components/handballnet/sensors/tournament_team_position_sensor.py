from typing import Any, Dict
from .base_sensor import HandballBaseSensor
from ..const import DOMAIN
from ..utils import normalize_logo_url
import logging

_LOGGER = logging.getLogger(__name__)

class HandballTournamentTeamPositionSensor(HandballBaseSensor):
    def __init__(self, hass, entry, tournament_id, team_data: Dict[str, Any]):
        # Use tournament_id for device grouping but team_id for unique identification
        super().__init__(hass, entry, tournament_id)
        self._tournament_id = tournament_id
        self._team_data = team_data
        self._state = None
        self._attributes = {}
        
        # Get tournament and team info
        tournament_name = entry.data.get("tournament_name", tournament_id)
        team_name = team_data.get("team_name", "")
        team_id = team_data.get("team_id", "")
        position = team_data.get("position", 0)
        
        # Set sensor name and unique ID
        self._attr_name = f"{tournament_name} Platz {position}: {team_name}"
        self._attr_unique_id = f"handball_tournament_{tournament_id}_position_{position}_{team_id}"
        self._attr_icon = "mdi:trophy-outline"
        
        # Set team logo as entity picture
        team_logo = team_data.get("team_logo")
        if team_logo:
            self._attr_entity_picture = normalize_logo_url(team_logo)
        
        # Override device info to group by tournament
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"tournament_{tournament_id}")},
            "name": f"Liga {tournament_name}",
            "manufacturer": "handball.net",
            "model": "Handball Tournament",
            "entry_type": "service"
        }

    @property
    def state(self) -> int | None:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attributes

    def update_team_data(self, team_data: Dict[str, Any]) -> None:
        """Update sensor with new team data"""
        self._team_data = team_data
        
        # Update entity picture if team logo changed
        team_logo = team_data.get("team_logo")
        if team_logo:
            self._attr_entity_picture = normalize_logo_url(team_logo)
        
        # Update state and attributes
        self._state = team_data.get("position")
        
        # Calculate additional stats
        games_played = team_data.get("games_played", 0)
        wins = team_data.get("wins", 0)
        draws = team_data.get("draws", 0)
        losses = team_data.get("losses", 0)
        
        # Calculate percentages
        win_percentage = round((wins / games_played) * 100, 1) if games_played > 0 else 0.0
        draw_percentage = round((draws / games_played) * 100, 1) if games_played > 0 else 0.0
        loss_percentage = round((losses / games_played) * 100, 1) if games_played > 0 else 0.0
        
        # Calculate averages
        goals_scored = team_data.get("goals_scored", 0)
        goals_conceded = team_data.get("goals_conceded", 0)
        avg_goals_scored = round(goals_scored / games_played, 2) if games_played > 0 else 0.0
        avg_goals_conceded = round(goals_conceded / games_played, 2) if games_played > 0 else 0.0
        
        self._attributes = {
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
            # Calculated statistics
            "win_percentage": win_percentage,
            "draw_percentage": draw_percentage,
            "loss_percentage": loss_percentage,
            "avg_goals_scored": avg_goals_scored,
            "avg_goals_conceded": avg_goals_conceded,
            "points_per_game": round(wins * 2 + draws / games_played, 2) if games_played > 0 else 0.0,
            # Position context
            "is_leader": team_data.get("position") == 1,
            "is_last_place": team_data.get("is_last_place", False),
            "is_promotion_zone": team_data.get("promoted", False),
            "is_relegation_zone": team_data.get("relegated", False)
        }

    async def async_update(self) -> None:
        """Update is handled by the main tournament table sensor"""
        # This sensor gets updated via update_team_data() method
        # called from the main tournament table sensor
        pass
