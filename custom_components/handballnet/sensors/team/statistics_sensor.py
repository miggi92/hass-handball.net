from typing import Any, Dict, List
from .base_sensor import HandballBaseSensor
from ...const import DOMAIN
import logging

_LOGGER = logging.getLogger(__name__)

class HandballStatisticsSensor(HandballBaseSensor):
    def __init__(self, hass, entry, team_id):
        super().__init__(hass, entry, team_id)
        self._team_id = team_id  # Explicitly set _team_id
        self._state = None
        self._attributes = {}

        # Use team name from config if available, fallback to team_id
        team_name = entry.data.get("team_name", team_id)
        self._attr_name = f"{team_name} Statistik"
        self._attr_unique_id = f"handball_team_{team_id}_statistics"
        self._attr_icon = "mdi:chart-bar"

    @property
    def state(self) -> str | None:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attributes

    async def async_update(self) -> None:
        try:
            matches = self.hass.data.get(DOMAIN, {}).get(self._team_id, {}).get("matches", [])
            if not matches:
                self._state = "Keine Spieldaten verfügbar"
                self._attributes = {}
                return

            self._calculate_statistics(matches)
        except Exception as e:
            _LOGGER.error("Error updating statistics for %s: %s", self._team_id, e)
            self._state = "Fehler beim Laden"
            self._attributes = {"error": str(e)}

    def _calculate_statistics(self, matches: List[Dict[str, Any]]) -> None:
        """Calculate statistics from match data"""
        total_matches = len(matches)
        wins = sum(1 for match in matches if match.get("result") == "win")
        draws = sum(1 for match in matches if match.get("result") == "draw")
        losses = sum(1 for match in matches if match.get("result") == "loss")

        goals_scored = sum(match.get("goals_scored", 0) for match in matches)
        goals_conceded = sum(match.get("goals_conceded", 0) for match in matches)

        self._state = f"{wins} Siege, {draws} Unentschieden, {losses} Niederlagen"
        self._attributes = {
            "total_matches": total_matches,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goals_scored": goals_scored,
            "goals_conceded": goals_conceded,
            "goal_difference": goals_scored - goals_conceded,
            "win_percentage": round((wins / total_matches) * 100, 1) if total_matches > 0 else 0.0,
            "draw_percentage": round((draws / total_matches) * 100, 1) if total_matches > 0 else 0.0,
            "loss_percentage": round((losses / total_matches) * 100, 1) if total_matches > 0 else 0.0,
        }