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
            _LOGGER.warning("No table data received for tournament %s", tournament_id)
            return None
        
        _LOGGER.debug("Table data for tournament %s: %s", tournament_id, table_data)
        _LOGGER.debug("Table data type: %s", type(table_data))
        
        # Check if table_data is a list
        if not isinstance(table_data, list):
            _LOGGER.warning("Table data is not a list: %s (type: %s)", table_data, type(table_data))
            return None
        
        _LOGGER.debug("Number of teams in table: %d", len(table_data))
        
        for position, team_entry in enumerate(table_data, 1):
            _LOGGER.debug("Processing position %d: %s (type: %s)", position, team_entry, type(team_entry))
            
            # Check if team_entry is a dictionary
            if not isinstance(team_entry, dict):
                _LOGGER.warning("Team entry at position %d is not a dict: %s (type: %s)", 
                              position, team_entry, type(team_entry))
                continue
            
            # Safely get team info
            try:
                team_info = team_entry.get("team")
                if team_info is None:
                    _LOGGER.warning("No team info at position %d", position)
                    continue
                    
                if not isinstance(team_info, dict):
                    _LOGGER.warning("Team info at position %d is not a dict: %s (type: %s)", 
                                  position, team_info, type(team_info))
                    continue
                
                team_id_from_entry = team_info.get("id")
                _LOGGER.debug("Team ID at position %d: %s (looking for: %s)", position, team_id_from_entry, team_id)
                
                if team_id_from_entry == team_id:
                    _LOGGER.info("Found team %s at position %d in tournament %s", team_id, position, tournament_id)
                    return {
                        "position": position,
                        "team_name": team_info.get("name", ""),
                        "points": team_entry.get("points", 0),
                        "games_played": team_entry.get("gamesPlayed", 0),
                        "wins": team_entry.get("wins", 0),
                        "draws": team_entry.get("draws", 0),
                        "losses": team_entry.get("losses", 0),
                        "goals_scored": team_entry.get("goalsScored", 0),
                        "goals_conceded": team_entry.get("goalsConceded", 0),
                        "goal_difference": team_entry.get("goalDifference", 0)
                    }
            except Exception as e:
                _LOGGER.error("Error processing team entry at position %d: %s", position, e)
                continue
        
        _LOGGER.warning("Team %s not found in table for tournament %s", team_id, tournament_id)
        return None
