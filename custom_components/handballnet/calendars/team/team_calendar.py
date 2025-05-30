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
        now = datetime.now(timezone.utc)
        
        # First check for currently running matches
        for match in matches:
            ts = match.get("startsAt")
            if not isinstance(ts, int):
                continue
            try:
                start = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
                end = start + timedelta(hours=2)
            except Exception:
                continue
            
            # If match is currently running (started but not ended)
            if start <= now <= end:
                return self._create_calendar_event(match, is_live=True)
        
        # If no current match, find next future match
        for match in sorted(matches, key=lambda x: x.get("startsAt", 0)):
            ts = match.get("startsAt")
            if not isinstance(ts, int):
                continue
            try:
                start = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
            except Exception:
                continue
            if start > now:
                return self._create_calendar_event(match)
        return None

    async def async_get_events(self, hass, start_date: datetime, end_date: datetime) -> list[CalendarEvent]:
        matches = self.hass.data[DOMAIN][self._team_id].get("matches", [])
        events: list[CalendarEvent] = []
        now = datetime.now(timezone.utc)
        
        for match in matches:
            ts = match.get("startsAt")
            if not isinstance(ts, int):
                continue
            try:
                start = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
                end = start + timedelta(hours=2)
            except Exception:
                continue
            
            if start_date <= start <= end_date:
                # Mark live games
                is_live = start <= now <= end
                event = self._create_calendar_event(match, is_live=is_live)
                if event:
                    events.append(event)
        return events
