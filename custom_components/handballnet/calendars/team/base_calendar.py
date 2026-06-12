from ..base_calendar import HandballBaseCalendar as BaseHandballCalendar
from ...const import DOMAIN

class HandballBaseCalendar(BaseHandballCalendar):
    """Base class for handball team calendars"""
    
    def __init__(self, hass, entry, team_id):
        super().__init__(hass, entry, team_id)
        self._team_id = team_id
        self._club_name = entry.data.get("club_name")
        self._team_variant = entry.data.get("team_variant")
        
        # Create team-specific device info
        team_name = entry.data.get("team_name", team_id)
        device_name = self._compose_device_name(team_name)
        self._attr_device_info = self._create_device_info(
            identifiers={(DOMAIN, self._team_id)},
            name=device_name,
            model="Handball Team"
        )

    def _compose_device_name(self, team_name: str) -> str:
        """Build stable device name, preferring club name and optional team variant."""
        base_name = self._club_name or team_name
        if self._team_variant:
            return f"{base_name} - {self._team_variant}"
        return base_name

    def update_device_name(self, team_name: str) -> None:
        """Update device name with actual team name"""
        if team_name and team_name != "":
            self._attr_device_info["name"] = self._compose_device_name(team_name)
