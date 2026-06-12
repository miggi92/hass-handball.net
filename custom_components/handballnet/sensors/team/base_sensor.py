from typing import Any
import re
from ..base_sensor import HandballBaseSensor as BaseHandballSensor
from ...const import DOMAIN, CONF_CLUB_ID
from ...utils import HandballNetUtils

class HandballBaseSensor(BaseHandballSensor):
    """Base class for handball team sensors"""

    def __init__(self, coordinator, entry, team_id, team_name, category=None):
        super().__init__(coordinator, entry, team_id, category)
        self.utils = HandballNetUtils()
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

    def _build_unique_id(self, sensor_type: str) -> str:
        team_slug = re.sub(r"[^a-z0-9]+", "_", self._team_name.lower()).strip("_")
        return f"{self._attr_config_entry_id}_{team_slug}_{sensor_type}"

    def _get_team_bucket(self) -> dict[str, Any]:
        return (self.coordinator.data or {}).get("teams", {}).get(self._team_id, {})

    def update_device_name(self, team_name: str) -> None:
        if team_name and team_name != "":
            self._attr_device_info["name"] = self._compose_device_name(team_name)

    def update_entity_picture(self, logo_url: str) -> None:
        if logo_url:
            self._attr_entity_picture = self.utils.normalize_logo_url(logo_url)
