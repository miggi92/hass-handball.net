from homeassistant.helpers.entity import Entity
from ..const import DOMAIN

class HandballBaseSensor(Entity):
    """Base class for all handball sensors"""
    
    def __init__(self, hass, entry, entity_id, category=None):
        self.hass = hass
        self._entity_id = entity_id
        self._category = category
        self._attr_config_entry_id = entry.entry_id
        
        # Set entity_category for better grouping
        if category:
            self._attr_entity_category = category

    def _create_device_info(self, identifiers, name, model):
        """Create device info dictionary"""
        return {
            "identifiers": identifiers,
            "name": name,
            "manufacturer": "handball.net",
            "model": model,
            "entry_type": "service"
        }

    def update_device_name(self, new_name: str) -> None:
        """Update device name - to be overridden if needed"""
        pass
