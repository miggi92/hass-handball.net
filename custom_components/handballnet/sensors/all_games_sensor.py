from typing import Any
from .base_sensor import HandballBaseSensor
from ..const import DOMAIN
from ..api import HandballNetAPI
from ..utils import get_next_match_info, get_last_match_info
import logging

_LOGGER = logging.getLogger(__name__)

class HandballAllGamesSensor(HandballBaseSensor):
    def __init__(self, hass, entry, team_id, api: HandballNetAPI):
        super().__init__(hass, entry, team_id)
        self._api = api
        self._state = None
        self._attributes = {}
        
        # Use team name from config if available, fallback to team_id
        team_name = entry.data.get("team_name", team_id)
        self._attr_name = f"Alle Spiele {team_name}"
        self._attr_unique_id = f"handball_all_games_{team_id}"

    @property
    def state(self) -> str | None:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attributes

    def update_entity_picture(self, logo_url: str) -> None:
        """Update entity picture with team logo"""
        if logo_url and logo_url.strip():
            self._attr_entity_picture = logo_url

    async def async_update(self) -> None:
        matches = await self._api.get_team_schedule(self._team_id)
        if matches is None:
            return

        team_data = await self._get_team_data(matches)
        match_data = self._process_matches(matches, team_data["team_name"])
        
        self._update_team_info(team_data)
        self._set_sensor_state(team_data["team_name"], len(matches), match_data)
        self._store_team_data(matches, match_data, team_data)

    async def _get_team_data(self, matches: list) -> dict:
        """Get team name and logo from matches or API"""
        team_name = None
        team_logo_url = self._api.extract_team_logo_url(matches, self._team_id)

        # Try to get team name from matches
        for match in matches:
            if match["homeTeam"]["id"] == self._team_id:
                team_name = match["homeTeam"]["name"]
                break
            elif match["awayTeam"]["id"] == self._team_id:
                team_name = match["awayTeam"]["name"]
                break

        # Fallback to API if no team info from matches
        if not team_name or not team_logo_url:
            team_info = await self._api.get_team_info(self._team_id)
            if team_info:
                team_name = team_name or team_info.get("name")
                team_logo_url = team_logo_url or team_info.get("logo")

        return {"team_name": team_name, "team_logo_url": team_logo_url}

    def _process_matches(self, matches: list, team_name: str) -> dict:
        """Process matches to separate home/away games and find next/last match"""
        heimspiele = []
        auswaertsspiele = []

        for match in matches:
            if match["homeTeam"]["id"] == self._team_id:
                heimspiele.append(match)
            elif match["awayTeam"]["id"] == self._team_id:
                auswaertsspiele.append(match)

        return {
            "heimspiele": heimspiele,
            "auswaertsspiele": auswaertsspiele,
            "next_match": get_next_match_info(matches),
            "last_match": get_last_match_info(matches)
        }

    def _update_team_info(self, team_data: dict) -> None:
        """Update device name and logo for all sensors"""
        team_name = team_data["team_name"]
        team_logo_url = team_data["team_logo_url"]
        
        if team_name:
            self.update_device_name(team_name)
            self._update_other_sensors(team_name, team_logo_url)
        
        if team_logo_url:
            self.update_entity_picture(team_logo_url)

    def _update_other_sensors(self, team_name: str, team_logo_url: str) -> None:
        """Update device name for other sensors in the same device"""
        sensors = self.hass.data.get(DOMAIN, {}).get(self._team_id, {}).get("sensors", [])
        for sensor in sensors:
            if hasattr(sensor, 'update_device_name'):
                sensor.update_device_name(team_name)
            # Logo nur für den "Alle Spiele" Sensor - nicht für andere Sensoren

    def _set_sensor_state(self, team_name: str, total_games: int, match_data: dict) -> None:
        """Set sensor state and attributes"""
        self._state = f"{team_name} ({total_games} Spiele)"
        self._attributes = {
            "team_name": team_name,
            "total_games": total_games,
            "home_games": len(match_data["heimspiele"]),
            "away_games": len(match_data["auswaertsspiele"]),
            "next_match": match_data["next_match"],
            "last_match": match_data["last_match"]
        }

    def _store_team_data(self, matches: list, match_data: dict, team_data: dict) -> None:
        """Store data in hass.data for other sensors"""
        team_storage = self.hass.data[DOMAIN][self._team_id]
        team_storage.update({
            "matches": matches,
            "heimspiele": match_data["heimspiele"],
            "auswaertsspiele": match_data["auswaertsspiele"],
            "team_name": team_data["team_name"],
            "team_logo_url": team_data["team_logo_url"]
        })
