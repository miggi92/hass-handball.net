from typing import Any, Dict, List
from .base_sensor import HandballBaseSensor
import logging

_LOGGER = logging.getLogger(__name__)

class HandballStatisticsSensor(HandballBaseSensor):
    def __init__(self, coordinator, entry, team_id, team_name):
        super().__init__(coordinator, entry, team_id, team_name)
        self._team_id = team_id

        display_name = self._resolve_display_name(team_name)
        self._attr_name = f"{display_name} Statistik"
        self._attr_unique_id = self._build_unique_id("statistics")
        self._attr_icon = "mdi:chart-bar"

    @property
    def state(self) -> str | None:
        return self._calculate_statistics(self._get_team_bucket().get("matches", []))[0]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._calculate_statistics(self._get_team_bucket().get("matches", []))[1]

    def _calculate_statistics(self, matches: List[Dict[str, Any]]) -> tuple[str | None, dict[str, Any]]:
        # Filter only finished matches (those with results)
        finished_matches = []
        upcoming_matches = []
        
        for match in matches:
            if match.get("state") == "Post" or (match.get("homeGoals") is not None and match.get("awayGoals") is not None):
                finished_matches.append(match)
            else:
                upcoming_matches.append(match)
        
        total_matches = len(finished_matches)
        wins = 0
        draws = 0
        losses = 0
        goals_scored = 0
        goals_conceded = 0
        
        for match in finished_matches:
            home_goals = match.get("homeGoals", 0) or 0
            away_goals = match.get("awayGoals", 0) or 0
            
            # Determine if this team is home or away
            is_home = match.get("isHomeMatch", False)
            
            if is_home:
                team_goals = home_goals
                opponent_goals = away_goals
            else:
                team_goals = away_goals
                opponent_goals = home_goals
            
            goals_scored += team_goals
            goals_conceded += opponent_goals
            
            # Determine result
            if team_goals > opponent_goals:
                wins += 1
            elif team_goals == opponent_goals:
                draws += 1
            else:
                losses += 1

        if total_matches == 0:
            return (
                "Noch keine beendeten Spiele",
                {
                    "total_matches": 0,
                    "finished_matches": 0,
                    "upcoming_matches": len(upcoming_matches),
                    "wins": 0,
                    "draws": 0,
                    "losses": 0,
                    "goals_scored": 0,
                    "goals_conceded": 0,
                    "goal_difference": 0,
                },
            )

        return (
            f"{wins} Siege, {draws} Unentschieden, {losses} Niederlagen",
            {
                "total_matches": len(matches),
                "finished_matches": total_matches,
                "upcoming_matches": len(upcoming_matches),
                "wins": wins,
                "draws": draws,
                "losses": losses,
                "goals_scored": goals_scored,
                "goals_conceded": goals_conceded,
                "goal_difference": goals_scored - goals_conceded,
                "win_percentage": round((wins / total_matches) * 100, 1),
                "draw_percentage": round((draws / total_matches) * 100, 1),
                "loss_percentage": round((losses / total_matches) * 100, 1),
                "avg_goals_scored": round(goals_scored / total_matches, 2),
                "avg_goals_conceded": round(goals_conceded / total_matches, 2),
            },
        )