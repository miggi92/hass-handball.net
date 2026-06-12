from typing import Any, List
from .base_sensor import HandballBaseSensor
from ...const import HEALTH_STATUS_UNKNOWN

class HandballHealthSensor(HandballBaseSensor):
    def __init__(self, coordinator, entry, team_id, team_name, api=None):
        super().__init__(coordinator, entry, team_id, team_name)
        self._team_id = team_id

        club_name = entry.data.get("club_name")
        display_name = f"{club_name} {team_name}" if club_name else team_name
        self._attr_name = f"{display_name} Health"
        self._attr_unique_id = self._build_unique_id("health")
        self._attr_icon = "mdi:heart-pulse"

    @property
    def state(self) -> str | None:
        return self._get_team_bucket().get("health", {}).get("state", HEALTH_STATUS_UNKNOWN)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        health = self._get_team_bucket().get("health", {})
        return health.get("attributes", {})