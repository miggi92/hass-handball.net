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
