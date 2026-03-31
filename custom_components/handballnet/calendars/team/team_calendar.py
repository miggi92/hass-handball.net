from homeassistant.components.calendar import CalendarEvent
from datetime import datetime, timezone
from .base_calendar import HandballBaseCalendar
from ...const import DOMAIN

class HandballTeamCalendar(HandballBaseCalendar):
    def __init__(self, hass, entry, team_id):
        super().__init__(hass, entry, team_id)
        
        # Use team name from config if available, fallback to team_id
        team_name = entry.data.get("team_name", team_id)
        self._attr_name = f"{team_name} Spielplan"
        self._attr_unique_id = f"handball_{team_id}_calendar"
        self._event = None

    @property
    def event(self) -> CalendarEvent | None:
        matches = self.hass.data[DOMAIN][self._team_id].get("matches", [])
        return self._get_current_or_next_event(matches)

    async def async_get_events(self, hass, start_date: datetime, end_date: datetime) -> list[CalendarEvent]:
        matches = self.hass.data[DOMAIN][self._team_id].get("matches", [])
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
