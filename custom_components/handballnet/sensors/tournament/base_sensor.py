from homeassistant.helpers.entity import Entity
from ...const import DOMAIN

class HandballBaseSensor(Entity):
    """Base class for handball tournament sensors"""
    
    def __init__(self, hass, entry, tournament_id, category=None):
        self.hass = hass
        self._tournament_id = tournament_id
        self._category = category
        self._attr_config_entry_id = entry.entry_id
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"tournament_{tournament_id}")},
            "name": f"Tournament {tournament_id}",
            "manufacturer": "handball.net",
            "model": "Handball Tournament",
            "entry_type": "service"
        }
        
        # Setze entity_category für bessere Gruppierung
        if category:
            self._attr_entity_category = category

    def update_device_name(self, tournament_name: str) -> None:
        """Update device name with actual tournament name"""
        if tournament_name and tournament_name != "":
            self._attr_device_info["name"] = f"Liga {tournament_name}"
