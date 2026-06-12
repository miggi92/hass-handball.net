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
            model="Handball Team",
        )

    def _compose_device_name(self, team_name: str) -> str:
        display_name = self._resolve_display_name(team_name)
        normalized_variant = (self._team_variant or "").strip()
        if normalized_variant and not display_name.endswith(f" {normalized_variant}"):
            return f"{display_name} {normalized_variant}".strip()
        return display_name

    def _resolve_display_name(self, team_name: str) -> str:
        """Build a stable display name for team entities."""
        normalized_team_name = (team_name or "").strip()
        normalized_club_name = (self._club_name or "").strip()

        if not normalized_club_name:
            return normalized_team_name or self._team_id

        if normalized_team_name and (
            normalized_team_name == normalized_club_name
            or normalized_team_name.startswith(f"{normalized_club_name} ")
        ):
            return normalized_team_name

        if normalized_team_name:
            return f"{normalized_club_name} {normalized_team_name}"

        return normalized_club_name

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
