from homeassistant.components.calendar import CalendarEvent
from datetime import datetime
from .base_calendar import HandballBaseCalendar
from ...const import DOMAIN

class HandballTournamentCalendar(HandballBaseCalendar):
    def __init__(self, hass, entry, tournament_id, coordinator=None):
        super().__init__(hass, entry, tournament_id, coordinator)
        
        # Use tournament name from config if available, fallback to tournament_id
        tournament_name = entry.data.get("tournament_name", tournament_id)
        self._attr_name = f"{tournament_name} Spielplan"
        self._attr_unique_id = f"handball_tournament_{tournament_id}_calendar"
        self._event = None

    @property
    def event(self) -> CalendarEvent | None:
        matches = self._get_matches()
        self._event = self._get_current_or_next_event(matches)
        return self._event

    async def async_update(self) -> None:
        matches = self._get_matches()
        self._event = self._get_current_or_next_event(matches)

    async def async_get_events(self, hass, start_date: datetime, end_date: datetime) -> list[CalendarEvent]:
        matches = self._get_matches()
        return self._collect_events_in_range(matches, start_date, end_date)

    def _get_matches(self) -> list[dict]:
        if self.coordinator is not None:
            matches = ((self.coordinator.data or {}).get("tournament", {}).get("matches"))
            if isinstance(matches, list):
                return matches

        tournament_key = f"tournament_{self._tournament_id}"
        return self.hass.data.get(DOMAIN, {}).get(tournament_key, {}).get("matches", [])
