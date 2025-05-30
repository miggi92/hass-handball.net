from typing import Any, List, Dict
from .base_sensor import HandballBaseSensor
from ..const import DOMAIN
from ..api import HandballNetAPI
from ..utils import normalize_logo_url
import logging

_LOGGER = logging.getLogger(__name__)

class HandballTournamentTableSensor(HandballBaseSensor):
    def __init__(self, hass, entry, tournament_id, api: HandballNetAPI):
        super().__init__(hass, entry, tournament_id)
        self._api = api
        self._tournament_id = tournament_id
        self._state = None
        self._attributes = {}
        
        # Use tournament name from config if available, fallback to tournament_id
        tournament_name = entry.data.get("tournament_name", tournament_id)
        self._attr_name = f"{tournament_name} Tabelle"
        self._attr_unique_id = f"handball_tournament_{tournament_id}_table"
        self._attr_icon = "mdi:trophy"

    @property
    def state(self) -> str | None:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attributes

    async def async_update(self) -> None:
        try:
            table_data = await self._api.get_league_table(self._tournament_id)
            if not table_data:
                self._state = "Keine Tabellendaten verfügbar"
                self._attributes = {}
                return

            tournament_info = await self._get_tournament_info()
            table_rows = await self._extract_table_rows_with_logos(table_data)
            
            self._set_sensor_state(tournament_info, table_rows)
            self._store_tournament_data(tournament_info, table_rows)
            
            # Update individual team position sensors
            await self._update_team_position_sensors(table_rows)

        except Exception as e:
            _LOGGER.error("Error updating tournament table for %s: %s", self._tournament_id, e)
            self._state = "Fehler beim Laden"
            self._attributes = {"error": str(e)}

    async def _get_tournament_info(self) -> Dict[str, Any]:
        """Get tournament information"""
        url = f"tournaments/{self._tournament_id}/table"
        data = await self._api._make_request(url)
        
        if data and "data" in data:
            tournament_data = data["data"].get("tournament", {})
            return {
                "name": tournament_data.get("name", self._tournament_id),
                "acronym": tournament_data.get("acronym", ""),
                "organization": tournament_data.get("organization", {}).get("name", ""),
                "logo": tournament_data.get("logo", "")
            }
        return {"name": self._tournament_id, "acronym": "", "organization": "", "logo": ""}

    async def _extract_table_rows_with_logos(self, table_data: Any) -> List[Dict[str, Any]]:
        """Extract and format table rows with team logos"""
        if isinstance(table_data, dict):
            rows = table_data.get("rows", [])
        elif isinstance(table_data, list):
            rows = table_data
        else:
            return []

        formatted_rows = []
        total_teams = len(rows)
        
        for row in rows:
            if not isinstance(row, dict):
                continue
                
            team_info = row.get("team", {})
            team_id = team_info.get("id")
            
            # Get team logo
            team_logo = None
            if team_id:
                try:
                    team_data = await self._api.get_team_info(team_id)
                    if team_data and team_data.get("logo"):
                        team_logo = team_data.get("logo")
                except Exception as e:
                    _LOGGER.debug("Could not fetch logo for team %s: %s", team_id, e)
            
            # Fallback to team logo from table data
            if not team_logo:
                team_logo = team_info.get("logo")
            
            position = row.get("rank", 0)
            formatted_row = {
                "position": position,
                "team_id": team_id,
                "team_name": team_info.get("name", ""),
                "team_acronym": team_info.get("acronym", ""),
                "team_logo": team_logo,
                "points": row.get("points", "0:0"),
                "games_played": row.get("games", 0),
                "wins": row.get("wins", 0),
                "draws": row.get("draws", 0),
                "losses": row.get("losses", 0),
                "goals_scored": row.get("goals", 0),
                "goals_conceded": row.get("goalsAgainst", 0),
                "goal_difference": row.get("goalDifference", 0),
                "promoted": row.get("promoted"),
                "relegated": row.get("relegated"),
                "is_last_place": position == total_teams
            }
            formatted_rows.append(formatted_row)

        return formatted_rows

    def _set_sensor_state(self, tournament_info: Dict[str, Any], table_rows: List[Dict[str, Any]]) -> None:
        """Set sensor state and attributes"""
        tournament_name = tournament_info["name"]
        total_teams = len(table_rows)
        
        if table_rows:
            leader = table_rows[0]
            self._state = f"{leader['team_name']} führt mit {leader['points']} Punkten"
        else:
            self._state = f"{tournament_name} - Keine Tabellendaten"

        self._attributes = {
            "tournament_name": tournament_name,
            "tournament_acronym": tournament_info["acronym"],
            "organization": tournament_info["organization"],
            "total_teams": total_teams,
            "table": table_rows[:10],  # Top 10 teams in attributes
            "leader": table_rows[0] if table_rows else None,
            "last_place": table_rows[-1] if table_rows else None
        }

    def _store_tournament_data(self, tournament_info: Dict[str, Any], table_rows: List[Dict[str, Any]]) -> None:
        """Store data in hass.data for other sensors"""
        if DOMAIN not in self.hass.data:
            self.hass.data[DOMAIN] = {}
        
        tournament_key = f"tournament_{self._tournament_id}"
        if tournament_key not in self.hass.data[DOMAIN]:
            self.hass.data[DOMAIN][tournament_key] = {}
            
        self.hass.data[DOMAIN][tournament_key].update({
            "tournament_info": tournament_info,
            "table_rows": table_rows,
            "sensors": self.hass.data[DOMAIN][tournament_key].get("sensors", [])
        })

    async def _update_team_position_sensors(self, table_rows: List[Dict[str, Any]]) -> None:
        """Update individual team position sensors"""
        tournament_key = f"tournament_{self._tournament_id}"
        sensors = self.hass.data.get(DOMAIN, {}).get(tournament_key, {}).get("sensors", [])
        
        # Find team position sensors
        from .tournament_team_position_sensor import HandballTournamentTeamPositionSensor
        team_position_sensors = [s for s in sensors if isinstance(s, HandballTournamentTeamPositionSensor)]
        
        # Update existing sensors with new data
        for team_data in table_rows:
            position = team_data.get("position")
            team_id = team_data.get("team_id")
            
            # Find matching sensor
            matching_sensor = None
            for sensor in team_position_sensors:
                if (sensor._team_data.get("position") == position or 
                    sensor._team_data.get("team_id") == team_id):
                    matching_sensor = sensor
                    break
            
            if matching_sensor:
                matching_sensor.update_team_data(team_data)
                matching_sensor.async_write_ha_state()
