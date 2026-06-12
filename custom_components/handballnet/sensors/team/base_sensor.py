from ..base_sensor import HandballBaseSensor as BaseHandballSensor
from ...const import DOMAIN
from ...utils import HandballNetUtils

class HandballBaseSensor(BaseHandballSensor):
    """Base class for handball team sensors"""

    def __init__(self, hass, entry, team_id, category=None):
        super().__init__(hass, entry, team_id, category)
        self.utils = HandballNetUtils()
        self._team_id = team_id  # Explicitly set _team_id for team sensors
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

    def update_entity_picture(self, logo_url: str) -> None:
        """Update entity picture with logo URL"""
        if logo_url:
            self._attr_entity_picture = self.utils.normalize_logo_url(logo_url)
