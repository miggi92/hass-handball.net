from homeassistant.helpers.update_coordinator import CoordinatorEntity
from ..const import DOMAIN

class HandballBaseSensor(CoordinatorEntity):
    """Base class for all handball sensors"""
    
    def __init__(self, coordinator, entry, entity_id, category=None):
        super().__init__(coordinator)
        self._entity_id = entity_id
        self._category = category
        self._attr_config_entry_id = entry.entry_id
        
        # Set entity_category for better grouping
        if category:
            self._attr_entity_category = category

    def _create_device_info(self, identifiers, name, model, via_device=None):
        """Create device info dictionary"""
        device_info = {
            "identifiers": identifiers,
            "name": name,
            "manufacturer": "handball.net",
            "model": model,
            "entry_type": "service"
        }

        if via_device is not None:
            device_info["via_device"] = via_device

        return device_info

    def update_device_name(self, new_name: str) -> None:
        """Update device name - to be overridden if needed"""
        pass
