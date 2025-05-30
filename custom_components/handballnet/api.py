import logging
from typing import Dict, List, Any, Optional
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.core import HomeAssistant
from .const import HANDBALL_NET_BASE_URL
from .utils import normalize_logo_url

_LOGGER = logging.getLogger(__name__)

class HandballNetAPI:
    """API client for handball.net"""
    
    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self.base_url = HANDBALL_NET_BASE_URL
        self.session = async_get_clientsession(hass)
    
    async def _make_request(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """Make HTTP request to handball.net API"""
        url = f"{self.base_url}/{endpoint}"
        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    _LOGGER.warning("HTTP error %s for endpoint %s", resp.status, endpoint)
                    return None
                return await resp.json()
        except Exception as e:
            _LOGGER.error("Request failed for endpoint %s: %s", endpoint, e)
            return None
    
    async def get_team_schedule(self, team_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get team schedule/matches"""
        data = await self._make_request(f"teams/{team_id}/schedule")
        return data.get("data", []) if data else None

    async def get_team_info(self, team_id: str) -> Optional[Dict[str, Any]]:
        """Get team information including logo"""
        data = await self._make_request(f"teams/{team_id}")
        if not data:
            return None
            
        team_data = data.get("data")
        if team_data and team_data.get("logo"):
            team_data["logo"] = normalize_logo_url(team_data["logo"])
        
        return team_data

    async def get_league_table(self, league_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get league table"""
        data = await self._make_request(f"tournaments/{league_id}/table")
        return data.get("data", []) if data else None

    async def get_live_ticker(self, game_id: str) -> Optional[Dict[str, Any]]:
        """Get live ticker events for a game"""
        data = await self._make_request(f"games/{game_id}/combined")
        return data.get("data", {}) if data else None

    def extract_team_logo_url(self, matches: List[Dict[str, Any]], team_id: str) -> Optional[str]:
        """Extract team logo URL from matches data"""
        if not matches:
            return None
            
        for match in matches:
            for team_key in ["homeTeam", "awayTeam"]:
                team = match.get(team_key, {})
                if team.get("id") == team_id:
                    logo_url = team.get("logo")
                    if logo_url:
                        return normalize_logo_url(logo_url)
        return None

    async def get_team_table_position(self, team_id: str, tournament_id: str) -> Optional[Dict[str, Any]]:
        """Get team position in league table"""
        table_data = await self.get_league_table(tournament_id)
        if not table_data:
            _LOGGER.warning("No table data received for tournament %s", tournament_id)
            return None
        
        return self._find_team_in_table(table_data, team_id, tournament_id)
    
    def _find_team_in_table(self, table_data: Any, team_id: str, tournament_id: str) -> Optional[Dict[str, Any]]:
        """Find team in league table data"""
        rows = self._extract_table_rows(table_data)
        if not rows:
            return None
        
        for team_entry in rows:
            if not isinstance(team_entry, dict):
                continue
                
            team_info = team_entry.get("team")
            if not isinstance(team_info, dict):
                continue
                
            if team_info.get("id") == team_id:
                return self._create_table_position_dict(team_entry, team_info)
        
        _LOGGER.warning("Team %s not found in table for tournament %s", team_id, tournament_id)
        return None
    
    def _extract_table_rows(self, table_data: Any) -> Optional[List[Dict[str, Any]]]:
        """Extract rows from table data structure"""
        if isinstance(table_data, dict):
            return table_data.get("rows", [])
        elif isinstance(table_data, list):
            return table_data
        else:
            _LOGGER.warning("Unexpected table data format: %s", type(table_data))
            return None
    
    def _create_table_position_dict(self, team_entry: Dict[str, Any], team_info: Dict[str, Any]) -> Dict[str, Any]:
        """Create standardized table position dictionary"""
        return {
            "position": team_entry.get("rank"),
            "team_name": team_info.get("name", ""),
            "points": team_entry.get("points", "0:0"),
            "games_played": team_entry.get("games", 0),
            "wins": team_entry.get("wins", 0),
            "draws": team_entry.get("draws", 0),
            "losses": team_entry.get("losses", 0),
            "goals_scored": team_entry.get("goals", 0),
            "goals_conceded": team_entry.get("goalsAgainst", 0),
            "goal_difference": team_entry.get("goalDifference", 0)
        }
