from homeassistant.components.calendar import CalendarEntity
from datetime import datetime, timedelta
from homeassistant.helpers.entity import Entity
from .const import DOMAIN

class HandballCalendar(CalendarEntity):
    def __init__(self, hass, team_id):
        self.hass = hass
        self._team_id = team_id
        self._name = f"Handball Spielplan {team_id}"
        self._matches = []

    @property
    def name(self):
        return self._name
    
    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self._team_id)},
            "name": f"Handball Team {self._team_id}",
            "manufacturer": "handball.net",
            "model": "Team Kalender + Sensor"
        }

    @property
    def event(self):
        now = datetime.now()
        matches = self.hass.data.get(DOMAIN, {}).get(self._team_id, {}).get("matches", [])
        for match in matches:
            start_raw = match.get("startsAt")
            if not isinstance(start_raw, str):
                continue
            try:
                start = datetime.fromisoformat(start_raw)
            except ValueError:
                continue

            if start > now:
                return {
                    "uid": match.get("id", "unknown"),
                    "start": start,
                    "end": start + timedelta(hours=2),
                    "summary": f"{match['homeTeam']['name']} vs {match['awayTeam']['name']}",
                    "description": f"Ort: {match.get('field', {}).get('name', 'unbekannt')}",
                    "all_day": False,
                }
        return None

    async def async_get_events(self, start_date: datetime, end_date: datetime):
        matches = self.hass.data.get(DOMAIN, {}).get(self._team_id, {}).get("matches", [])
        events = []
        for match in matches:
            start_raw = match.get("startsAt")
            if not isinstance(start_raw, str):
                continue
            try:
                start = datetime.fromisoformat(start_raw)
            except ValueError:
                continue

            end = start + timedelta(hours=2)
            if start >= start_date and start <= end_date:
                events.append({
                    "uid": match.get("id", "unknown"),
                    "start": start,
                    "end": end,
                    "summary": f"{match['homeTeam']['name']} vs {match['awayTeam']['name']}",
                    "description": f"Ort: {match.get('field', {}).get('name', 'unbekannt')}",
                    "all_day": False,
                })
        return events

    async def async_update(self):
        # Es ist kein Update nötig, da der Sensor die Daten liefert
        pass


async def async_setup_entry(hass, entry, async_add_entities):
    team_id = entry.data["team_id"]
    async_add_entities([HandballCalendar(hass, team_id)], update_before_add=True)
