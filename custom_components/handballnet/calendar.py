from homeassistant.components.calendar import CalendarEntity
from datetime import datetime, timedelta
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    team_id = entry.data["team_id"]
    matches = hass.data[DOMAIN][team_id].get("matches", [])
    async_add_entities([HandballCalendar(hass, team_id, matches)])

class HandballCalendar(CalendarEntity):
    def __init__(self, hass, team_id):
        self.hass = hass
        self._team_id = team_id
        self._name = f"Handball Spielplan {team_id}"

    @property
    def name(self):
        return self._name

    async def async_get_events(self, start_date: datetime, end_date: datetime):
        matches = self.hass.data.get(DOMAIN, {}).get(self._team_id, {}).get("matches", [])
        events = []
        for match in matches:
            start = datetime.fromtimestamp(match["startsAt"] / 1000)
            end = start + timedelta(hours=2)

            if start >= start_date and start <= end_date:
                events.append({
                    "uid": match["id"],
                    "start": start,
                    "end": end,
                    "summary": f"{match['homeTeam']['name']} vs {match['awayTeam']['name']}",
                    "description": f"Ort: {match.get('field', {}).get('name', 'unbekannt')}",
                    "all_day": False,
                })
        return events
