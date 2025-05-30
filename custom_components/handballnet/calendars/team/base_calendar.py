from ..base_calendar import HandballBaseCalendar as BaseHandballCalendar
from ...const import DOMAIN

class HandballBaseCalendar(BaseHandballCalendar):
    """Base class for handball team calendars"""
    
    def __init__(self, hass, entry, team_id):
        super().__init__(hass, entry, team_id)
        self._team_id = team_id
        
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
