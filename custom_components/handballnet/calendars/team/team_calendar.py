from homeassistant.components.calendar import CalendarEvent
from datetime import datetime, timezone
from .base_calendar import HandballBaseCalendar
from ...const import DOMAIN


class HandballTeamCalendar(HandballBaseCalendar):
    def __init__(self, hass, entry, team_id, team_name, coordinator=None):
        super().__init__(hass, entry, team_id, team_name, coordinator)

        display_name = self._resolve_display_name(team_name)
        self._attr_name = f"{display_name} Spielplan"
        self._attr_unique_id = self._build_unique_id("calendar")
        self._event = None

    @property
    def event(self) -> CalendarEvent | None:
        matches = self._get_matches()
        return self._get_current_or_next_event(matches)

    async def async_get_events(
        self, hass, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        matches = self._get_matches()
        events: list[CalendarEvent] = []
        now = datetime.now(timezone.utc)

        for match in matches:
            match_window = self._get_match_window(match)
            if not match_window:
                continue
            start, end = match_window

            if start_date <= start <= end_date:
                # Mark live games
                is_live = start <= now <= end
                event = self._create_calendar_event(match, is_live=is_live)
                if event:
                    events.append(event)
        return events

    def _get_matches(self) -> list[dict]:
        if self.coordinator is not None:
            matches = (
                (self.coordinator.data or {})
                .get("teams", {})
                .get(self._team_id, {})
                .get("matches")
            )
            if isinstance(matches, list):
                return matches

        return self.hass.data.get(DOMAIN, {}).get(self._team_id, {}).get("matches", [])
