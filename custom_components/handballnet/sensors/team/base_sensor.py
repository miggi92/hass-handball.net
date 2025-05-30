from ..base_sensor import HandballBaseSensor as BaseHandballSensor
from ...const import DOMAIN

class HandballBaseSensor(BaseHandballSensor):
    """Base class for handball team sensors"""
    
    def __init__(self, hass, entry, team_id, category=None):
        super().__init__(hass, entry, team_id, category)
        self._team_id = team_id  # Explicitly set _team_id for team sensors
        
        # Create team-specific device info
        team_name = entry.data.get("team_name", team_id)
        self._attr_device_info = self._create_device_info(
            identifiers={(DOMAIN, self._team_id)},
            name=f"{team_name}",
            model="Handball Team"
        )

    def update_device_name(self, team_name: str) -> None:
        """Update device name with actual team name"""
        if team_name and team_name != "":
            self._attr_device_info["name"] = f"{team_name}"
