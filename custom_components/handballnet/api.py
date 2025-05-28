import logging
from typing import Dict, List, Any, Optional
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

class HandballNetAPI:
    """API client for handball.net"""
    
    def __init__(self, hass: HomeAssistant):
        self.hass = hass
        self.base_url = "https://www.handball.net/a/sportdata/1"
        self.session = async_get_clientsession(hass)
    
    async def get_team_schedule(self, team_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get team schedule/matches"""
        url = f"{self.base_url}/teams/{team_id}/schedule"
        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    _LOGGER.warning("Error fetching team schedule from handball.net: %s", resp.status)
                    return None
                data = await resp.json()
                return data.get("data", [])
        except Exception as e:
            _LOGGER.error("Error fetching team schedule: %s", e)
            return None
    
    async def get_league_table(self, league_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get league table"""
        url = f"{self.base_url}/tournaments/{league_id}/table"
        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    _LOGGER.warning("Error fetching league table from handball.net: %s", resp.status)
                    return None
                data = await resp.json()
                return data.get("data", [])
        except Exception as e:
            _LOGGER.error("Error fetching league table: %s", e)
            return None
    
    async def get_team_info(self, team_id: str) -> Optional[Dict[str, Any]]:
        """Get team information"""
        url = f"{self.base_url}/teams/{team_id}"
        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    _LOGGER.warning("Error fetching team info from handball.net: %s", resp.status)
                    return None
                data = await resp.json()
                return data.get("data")
        except Exception as e:
            _LOGGER.error("Error fetching team info: %s", e)
            return None
    
    async def get_team_table_position(self, team_id: str, tournament_id: str) -> Optional[Dict[str, Any]]:
        """Get team position in league table"""
        table_data = await self.get_league_table(tournament_id)
        if table_data is None:
            return None
        
        for position, team_entry in enumerate(table_data, 1):
            if team_entry.get("team", {}).get("id") == team_id:
                return {
                    "position": position,
                    "team_name": team_entry.get("team", {}).get("name", ""),
                    "points": team_entry.get("points", 0),
                    "games_played": team_entry.get("gamesPlayed", 0),
                    "wins": team_entry.get("wins", 0),
                    "draws": team_entry.get("draws", 0),
                    "losses": team_entry.get("losses", 0),
                    "goals_scored": team_entry.get("goalsScored", 0),
                    "goals_conceded": team_entry.get("goalsConceded", 0),
                    "goal_difference": team_entry.get("goalDifference", 0)
                }
        return None
