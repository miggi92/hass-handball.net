from ..base_sensor import HandballBaseSensor as BaseHandballSensor
from ...const import DOMAIN

class HandballBaseSensor(BaseHandballSensor):
    """Base class for handball tournament sensors"""
    
    def __init__(self, hass, entry, tournament_id, category=None):
        super().__init__(hass, entry, tournament_id, category)
        self._tournament_id = tournament_id
        
        # Create tournament-specific device info
        tournament_name = entry.data.get("tournament_name", tournament_id)
        self._attr_device_info = self._create_device_info(
            identifiers={(DOMAIN, f"tournament_{tournament_id}")},
            name=f"Liga {tournament_name}",
            model="Handball Tournament"
        )

    def update_device_name(self, tournament_name: str) -> None:
        """Update device name with actual tournament name"""
        if tournament_name and tournament_name != "":
            self._attr_device_info["name"] = f"Liga {tournament_name}"
