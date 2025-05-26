from homeassistant.components.calendar import CalendarEntity
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
        self._name = f"Handball Spielplan {team_id}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, team_id)},
            "name": f"Handball Team {team_id}",
            "manufacturer": "handball.net",
            "model": "Team Kalender + Sensor",
            "entry_type": "service"
        }
        self._attr_config_entry_id = entry.entry_id

    @property
    def name(self):
        return self._name

    @property
    def event(self):
        matches = self.hass.data[DOMAIN][self._team_id].get("matches", [])
        now = datetime.now()
        for match in matches:
            start_str = match.get("startsAt")
            if not start_str or not isinstance(start_str, str):
                continue
            start = datetime.fromisoformat(start_str)
            if start > now:
                return {
                    "uid": match["id"],
                    "start": start,
                    "end": start + timedelta(hours=2),
                    "summary": f"{match['homeTeam']['name']} vs {match['awayTeam']['name']}",
                    "description": match.get("field", {}).get("name", "unbekannt"),
                    "all_day": False
                }
        return None

    async def async_get_events(self, start_date, end_date):
        matches = self.hass.data[DOMAIN][self._team_id].get("matches", [])
        events = []
        for match in matches:
            start_str = match.get("startsAt")
            if not start_str or not isinstance(start_str, str):
                continue
            start = datetime.fromisoformat(start_str)
            if start >= start_date and start <= end_date:
                events.append({
                    "uid": match["id"],
                    "start": start,
                    "end": start + timedelta(hours=2),
                    "summary": f"{match['homeTeam']['name']} vs {match['awayTeam']['name']}",
                    "description": match.get("field", {}).get("name", "unbekannt"),
                    "all_day": False,
                })
        return events
