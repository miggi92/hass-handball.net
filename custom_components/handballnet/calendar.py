from __future__ import annotations

from datetime import datetime, timedelta
import logging
from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the calendar platform for handballnet."""
    team_id = entry.data["team_id"]
    async_add_entities([HandballCalendar(hass, team_id)], update_before_add=True)


class HandballCalendar(CalendarEntity):
    def __init__(self, hass: HomeAssistant, team_id: str) -> None:
        self.hass = hass
        self._team_id = team_id
        self._name = f"Handball Spielplan {team_id}"

    @property
    def name(self) -> str:
        return self._name

    @property
    def event(self) -> CalendarEvent | None:
        """Return the next upcoming event."""
        matches = self.hass.data.get(DOMAIN, {}).get(self._team_id, {}).get("matches", [])
        now = datetime.now()

        future_matches = [
            match for match in matches
            if datetime.fromisoformat(match["startsAt"]) > now
        ]

        if not future_matches:
            return None

        next_match = sorted(future_matches, key=lambda m: m["startsAt"])[0]
        start = datetime.fromisoformat(next_match["startsAt"])
        end = start + timedelta(hours=2)

        return CalendarEvent(
            summary=f"{next_match['homeTeam']['name']} vs {next_match['awayTeam']['name']}",
            start=start,
            end=end,
            description=f"Ort: {next_match.get('field', {}).get('name', 'unbekannt')}",
            location=next_match.get('field', {}).get('name', ''),
        )

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        """Return all events in the given time range."""
        matches = self.hass.data.get(DOMAIN, {}).get(self._team_id, {}).get("matches", [])
        events = []

        for match in matches:
            start = datetime.fromisoformat(match["startsAt"])
            end = start + timedelta(hours=2)
            if start >= start_date and start <= end_date:
                events.append(CalendarEvent(
                    summary=f"{match['homeTeam']['name']} vs {match['awayTeam']['name']}",
                    start=start,
                    end=end,
                    description=f"Ort: {match.get('field', {}).get('name', 'unbekannt')}",
                    location=match.get('field', {}).get('name', ''),
                ))

        return events
