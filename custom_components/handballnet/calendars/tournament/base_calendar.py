from ..base_calendar import HandballBaseCalendar as BaseHandballCalendar
from ...const import DOMAIN

class HandballBaseCalendar(BaseHandballCalendar):
    """Base class for handball tournament calendars"""
    
    def __init__(self, hass, entry, tournament_id):
        super().__init__(hass, entry, tournament_id)
        self._tournament_id = tournament_id
        
        # Create tournament-specific device info
        tournament_name = entry.data.get("tournament_name", tournament_id)
        self._attr_device_info = self._create_device_info(
            identifiers={(DOMAIN, f"tournament_{tournament_id}")},
            name=f"{tournament_name}",
            model="Handball Tournament"
        )

    def update_device_name(self, tournament_name: str) -> None:
        """Update device name with actual tournament name"""
        if tournament_name and tournament_name != "":
            self._attr_device_info["name"] = f"{tournament_name}"
