from datetime import datetime, timezone, timedelta
from typing import Any
from .base_sensor import HandballBaseSensor
from ..const import DOMAIN
from ..api import HandballNetAPI
import logging

_LOGGER = logging.getLogger(__name__)

class HandballHealthSensor(HandballBaseSensor):
    def __init__(self, hass, entry, team_id, api: HandballNetAPI):
        super().__init__(hass, entry, team_id)
        self._api = api
        self._state = "unknown"
        self._attributes = {}
        self._attr_name = f"Handball API Status {team_id}"
        self._attr_unique_id = f"handball_health_{team_id}"
        self._attr_icon = "mdi:heart-pulse"
        self._last_successful_update = None
        self._error_count = 0

    @property
    def state(self) -> str:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attributes

    async def async_update(self) -> None:
        now = datetime.now(timezone.utc)
        errors = []
        
        try:
            # Test basic connectivity
            team_info = await self._api.get_team_info(self._team_id)
            if team_info:
                self._last_successful_update = now
                self._error_count = 0
            else:
                errors.append("Team info not available")
                self._error_count += 1

            # Test schedule endpoint
            schedule = await self._api.get_team_schedule(self._team_id)
            if not schedule:
                errors.append("Schedule not available")
                self._error_count += 1

            # Determine health status
            if not errors:
                self._state = "healthy"
            elif len(errors) == 1:
                self._state = "degraded"
            else:
                self._state = "unhealthy"

            # Check if we haven't had a successful update in a while
            if self._last_successful_update:
                time_since_success = now - self._last_successful_update
                if time_since_success > timedelta(hours=2):
                    self._state = "stale"
                    errors.append(f"No successful update for {time_since_success}")

            self._attributes = {
                "team_id": self._team_id,
                "errors": errors,
                "error_count": self._error_count,
                "last_successful_update": self._last_successful_update.isoformat() if self._last_successful_update else None,
                "last_check": now.isoformat(),
                "team_available": team_info is not None,
                "schedule_available": schedule is not None and len(schedule) > 0
            }

        except Exception as e:
            _LOGGER.error("Error checking health for team %s: %s", self._team_id, e)
            self._state = "error"
            self._error_count += 1
            self._attributes = {
                "team_id": self._team_id,
                "errors": [f"Health check failed: {str(e)}"],
                "error_count": self._error_count,
                "last_check": now.isoformat(),
                "exception": str(e)
            }
