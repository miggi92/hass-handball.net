import re
from ..base_calendar import HandballBaseCalendar as BaseHandballCalendar
from ...const import DOMAIN, CONF_CLUB_ID

class HandballBaseCalendar(BaseHandballCalendar):
    """Base class for handball team calendars"""
    
    def __init__(self, hass, entry, team_id, team_name):
        super().__init__(hass, entry, team_id)
        self._team_id = team_id
        self._team_name = team_name
        self._club_name = entry.data.get("club_name")
        self._club_id = entry.data.get(CONF_CLUB_ID, entry.entry_id)
        self._team_variant = entry.data.get("team_variant")
        
        device_name = self._compose_device_name(team_name)
        self._attr_device_info = self._create_device_info(
            identifiers={(DOMAIN, f"{entry.entry_id}_{team_name}")},
            via_device=(DOMAIN, self._club_id),
            name=device_name,
            model="Handball Team"
        )

    def _compose_device_name(self, team_name: str) -> str:
        base_name = self._club_name or team_name
        if self._team_variant and team_name != self._team_variant:
            return f"{base_name} {self._team_variant}"
        return base_name

    def update_device_name(self, team_name: str) -> None:
        if team_name and team_name != "":
            self._attr_device_info["name"] = self._compose_device_name(team_name)

    def _build_unique_id(self, suffix: str) -> str:
        team_slug = re.sub(r"[^a-z0-9]+", "_", self._team_name.lower()).strip("_")
        return f"{self._attr_config_entry_id}_{team_slug}_{suffix}"
