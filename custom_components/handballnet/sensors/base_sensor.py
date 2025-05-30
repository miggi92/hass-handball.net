from homeassistant.helpers.entity import Entity
from ..const import DOMAIN


class HandballBaseSensor(Entity):
    """Base class for handball sensors"""
    
    def __init__(self, hass, entry, team_id):
        self.hass = hass
        self._team_id = team_id
        self._attr_config_entry_id = entry.entry_id
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._team_id)},
            "name": f"Handball Team {self._team_id}",
            "manufacturer": "handball.net",
            "model": "Handball Team",
            "entry_type": "service"
        }

    def update_device_name(self, team_name: str) -> None:
        """Update device name with actual team name"""
        if team_name and team_name != "":
            self._attr_device_info["name"] = f"Handball {team_name}"
            
    def update_entity_picture(self, logo_url: str) -> None:
        """Update entity picture with team logo"""
        if logo_url and logo_url.strip():
            self._attr_entity_picture = logo_url
