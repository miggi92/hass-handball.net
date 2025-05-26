from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from datetime import datetime, timedelta
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    team_id = entry.data["team_id"]
    entity = HandballCalendar(hass, entry, team_id)
    async_add_entities([entity], update_before_add=True)

class HandballCalendar(CalendarEntity):
    def __init__(self, hass, entry, team_id):
        self.hass = hass
        self._team_id = team_id
        self._attr_name = f"Handball Spielplan {team_id}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, team_id)},
            "name": f"Handball Team {team_id}",
            "manufacturer": "handball.net",
            "model": "Team Kalender + Sensor",
            "entry_type": "service"
        }
        self._attr_config_entry_id = entry.entry_id

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        matches = self.hass.data[DOMAIN][self._team_id].get("matches", [])
        now = datetime.now()
        for match in matches:
            start_str = match.get("startsAt")
            if not isinstance(start_str, str):
                continue
            try:
                start = datetime.fromisoformat(start_str)
            except ValueError:
                continue

            if start > now:
                return CalendarEvent(
                    summary=f"{match['homeTeam']['name']} vs {match['awayTeam']['name']}",
                    start=start,
                    end=start + timedelta(hours=2),
                    description=match.get("field", {}).get("name", "unbekannt"),
                    location=match.get("field", {}).get("name", "")
                )
        return None

    async def async_get_events(self, start_date: datetime, end_date: datetime) -> list[CalendarEvent]:
        matches = self.hass.data[DOMAIN][self._team_id].get("matches", [])
        events: list[CalendarEvent] = []
        for match in matches:
            start_str = match.get("startsAt")
            if not isinstance(start_str, str):
                continue
            try:
                start = datetime.fromisoformat(start_str)
            except ValueError:
                continue

            if start_date <= start <= end_date:
                events.append(CalendarEvent(
                    summary=f"{match['homeTeam']['name']} vs {match['awayTeam']['name']}",
                    start=start,
                    end=start + timedelta(hours=2),
                    description=match.get("field", {}).get("name", "unbekannt"),
                    location=match.get("field", {}).get("name", "")
                ))
        return events
