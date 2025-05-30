from datetime import datetime, timezone, timedelta
from typing import Any, List
from .base_sensor import HandballBaseSensor
from ..const import (
    DOMAIN, HEALTH_CHECK_STALE_HOURS,
    HEALTH_STATUS_HEALTHY, HEALTH_STATUS_DEGRADED, HEALTH_STATUS_UNHEALTHY,
    HEALTH_STATUS_STALE, HEALTH_STATUS_ERROR, HEALTH_STATUS_UNKNOWN
)
from ..api import HandballNetAPI
import logging

_LOGGER = logging.getLogger(__name__)

class HandballHealthSensor(HandballBaseSensor):
    def __init__(self, hass, entry, team_id, api: HandballNetAPI):
        super().__init__(hass, entry, team_id)
        self._api = api
        self._state = HEALTH_STATUS_UNKNOWN
        self._attributes = {}
        
        # Use team name from config if available, fallback to team_id
        team_name = entry.data.get("team_name", team_id)
        self._attr_name = f"API Status {team_name}"
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
        
        try:
            errors = await self._perform_health_checks()
            self._update_health_status(errors, now)
            self._set_success_attributes(errors, now)
        except Exception as e:
            self._handle_health_check_error(e, now)

    async def _perform_health_checks(self) -> List[str]:
        """Perform all health checks and return list of errors"""
        errors = []
        
        # Test team info endpoint
        team_info = await self._api.get_team_info(self._team_id)
        if not team_info:
            errors.append("Team info not available")
            self._error_count += 1
        else:
            self._last_successful_update = datetime.now(timezone.utc)
            self._error_count = 0

        # Test schedule endpoint
        schedule = await self._api.get_team_schedule(self._team_id)
        if not schedule:
            errors.append("Schedule not available")
            self._error_count += 1

        return errors

    def _update_health_status(self, errors: List[str], now: datetime) -> None:
        """Determine health status based on errors and staleness"""
        if self._is_data_stale(now):
            self._state = HEALTH_STATUS_STALE
            errors.append(self._get_staleness_message(now))
        elif not errors:
            self._state = HEALTH_STATUS_HEALTHY
        elif len(errors) == 1:
            self._state = HEALTH_STATUS_DEGRADED
        else:
            self._state = HEALTH_STATUS_UNHEALTHY

    def _is_data_stale(self, now: datetime) -> bool:
        """Check if data is considered stale"""
        if not self._last_successful_update:
            return False
        
        time_since_success = now - self._last_successful_update
        return time_since_success > timedelta(hours=HEALTH_CHECK_STALE_HOURS)

    def _get_staleness_message(self, now: datetime) -> str:
        """Get staleness error message"""
        time_since_success = now - self._last_successful_update
        return f"No successful update for {time_since_success}"

    def _set_success_attributes(self, errors: List[str], now: datetime) -> None:
        """Set attributes for successful health check"""
        self._attributes = {
            "team_id": self._team_id,
            "status": self._state,
            "errors": errors,
            "error_count": self._error_count,
            "last_successful_update": self._last_successful_update.isoformat() if self._last_successful_update else None,
            "last_check": now.isoformat(),
            "is_healthy": self._state == HEALTH_STATUS_HEALTHY
        }

    def _handle_health_check_error(self, error: Exception, now: datetime) -> None:
        """Handle health check errors"""
        _LOGGER.error("Error checking health for team %s: %s", self._team_id, error)
        self._state = HEALTH_STATUS_ERROR
        self._error_count += 1
        self._attributes = {
            "team_id": self._team_id,
            "status": self._state,
            "errors": [f"Health check failed: {str(error)}"],
            "error_count": self._error_count,
            "last_check": now.isoformat(),
            "exception": str(error),
            "is_healthy": False
        }
