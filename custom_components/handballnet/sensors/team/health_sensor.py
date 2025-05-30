from datetime import datetime, timezone, timedelta
from typing import Any, List
from ..base_sensor import HandballBaseSensor
from ...const import (
    DOMAIN, HEALTH_CHECK_STALE_HOURS,
    HEALTH_STATUS_HEALTHY, HEALTH_STATUS_DEGRADED, HEALTH_STATUS_UNHEALTHY,
    HEALTH_STATUS_STALE, HEALTH_STATUS_ERROR, HEALTH_STATUS_UNKNOWN
)
from ...api import HandballNetAPI
import logging

_LOGGER = logging.getLogger(__name__)

class HandballHealthSensor(HandballBaseSensor):
    def __init__(self, hass, entry, team_id, api: HandballNetAPI):
        super().__init__(hass, entry, team_id)
        self._api = api
        self._state = None
        self._attributes = {}

        # Use team name from config if available, fallback to team_id
        team_name = entry.data.get("team_name", team_id)
        self._attr_name = f"{team_name} Health"
        self._attr_unique_id = f"handball_team_{team_id}_health"
        self._attr_icon = "mdi:heart-pulse"

    @property
    def state(self) -> str | None:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attributes

    async def async_update(self) -> None:
        try:
            matches = self.hass.data.get(DOMAIN, {}).get(self._team_id, {}).get("matches", [])
            if not matches:
                self._state = HEALTH_STATUS_UNKNOWN
                self._attributes = {}
                return

            now = datetime.now(timezone.utc)
            stale_threshold = now - timedelta(hours=HEALTH_CHECK_STALE_HOURS)

            # Check for stale data
            if all(datetime.fromtimestamp(match.get("lastUpdated", 0) / 1000, tz=timezone.utc) < stale_threshold for match in matches):
                self._state = HEALTH_STATUS_STALE
                self._attributes = {}
                return

            # Check for errors in matches
            if any(match.get("error") for match in matches):
                self._state = HEALTH_STATUS_ERROR
                self._attributes = {}
                return

            # Check for unhealthy conditions
            if any(match.get("status") == "unhealthy" for match in matches):
                self._state = HEALTH_STATUS_UNHEALTHY
                self._attributes = {}
                return

            # Check for degraded conditions
            if any(match.get("status") == "degraded" for match in matches):
                self._state = HEALTH_STATUS_DEGRADED
                self._attributes = {}
                return

            # If none of the above, the system is healthy
            self._state = HEALTH_STATUS_HEALTHY
            self._attributes = {
                "last_updated": max(match.get("lastUpdated", 0) for match in matches),
                "total_matches": len(matches),
                "healthy_matches": sum(1 for match in matches if match.get("status") == "healthy"),
                "degraded_matches": sum(1 for match in matches if match.get("status") == "degraded"),
                "unhealthy_matches": sum(1 for match in matches if match.get("status") == "unhealthy"),
                "stale_matches": sum(1 for match in matches if datetime.fromtimestamp(match.get("lastUpdated", 0) / 1000, tz=timezone.utc) < stale_threshold),
            }

        except Exception as e:
            _LOGGER.error("Error updating health sensor for %s: %s", self._team_id, e)
            self._state = HEALTH_STATUS_ERROR
            self._attributes = {"error": str(e)}