from typing import Any, List
from .base_sensor import HandballBaseSensor
from ...const import HEALTH_STATUS_UNKNOWN


class HandballHealthSensor(HandballBaseSensor):
    def __init__(self, coordinator, entry, team_id, team_name, api=None):
        super().__init__(coordinator, entry, team_id, team_name)
        self._team_id = team_id

        display_name = self._resolve_display_name(team_name)
        self._attr_name = f"{display_name} Health"
        self._attr_unique_id = self._build_unique_id("health")
        self._attr_icon = "mdi:heart-pulse"

    @property
    def state(self) -> str | None:
        return (
            self._get_team_bucket()
            .get("health", {})
            .get("state", HEALTH_STATUS_UNKNOWN)
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        health = self._get_team_bucket().get("health", {})
        attributes = dict(health.get("attributes", {}))

        team_perf = self._get_team_bucket().get("perf", {})
        if team_perf:
            attributes["performance"] = team_perf

        coordinator_perf = (self.coordinator.data or {}).get("perf", {})
        if coordinator_perf:
            attributes["coordinator_performance"] = self._compact_coordinator_perf(
                coordinator_perf
            )

        return attributes

    def _compact_coordinator_perf(
        self, coordinator_perf: dict[str, Any]
    ) -> dict[str, Any]:
        compact_perf: dict[str, Any] = {}

        updated_at = coordinator_perf.get("updated_at")
        if updated_at:
            compact_perf["updated_at"] = updated_at

        phases_ms = coordinator_perf.get("phases_ms")
        if isinstance(phases_ms, dict):
            compact_perf["phases_ms"] = phases_ms

        team_bucket_ms = coordinator_perf.get("team_bucket_ms")
        if isinstance(team_bucket_ms, dict):
            current_team_time = team_bucket_ms.get(self._team_id)
            if current_team_time is not None:
                compact_perf["current_team_bucket_update_ms"] = current_team_time

            # Include only the three slowest teams for quick hotspot visibility.
            slowest_teams = sorted(
                (
                    (team_id, timing)
                    for team_id, timing in team_bucket_ms.items()
                    if isinstance(timing, (int, float))
                ),
                key=lambda item: item[1],
                reverse=True,
            )[:3]
            if slowest_teams:
                compact_perf["slowest_team_bucket_updates_ms"] = {
                    team_id: timing for team_id, timing in slowest_teams
                }

        return compact_perf
