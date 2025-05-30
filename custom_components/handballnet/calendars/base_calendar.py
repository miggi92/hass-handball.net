from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from datetime import datetime, timedelta, timezone
from ..const import DOMAIN

class HandballBaseCalendar(CalendarEntity):
    """Base class for all handball calendars"""
    
    def __init__(self, hass, entry, entity_id):
        self.hass = hass
        self._entity_id = entity_id
        self._attr_config_entry_id = entry.entry_id
        
    def _create_device_info(self, identifiers, name, model):
        """Create device info dictionary"""
        return {
            "identifiers": identifiers,
            "name": name,
            "manufacturer": "handball.net",
            "model": model,
            "entry_type": "service"
        }

    def update_device_name(self, new_name: str) -> None:
        """Update device name - to be overridden if needed"""
        pass

    def _create_calendar_event(self, match_data: dict, is_live: bool = False) -> CalendarEvent:
        """Create a calendar event from match data"""
        ts = match_data.get("startsAt")
        if not isinstance(ts, int):
            return None
            
        try:
            start = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
            end = start + timedelta(hours=2)
        except Exception:
            return None

        home_team = match_data.get("homeTeam", {}).get("name", "")
        away_team = match_data.get("awayTeam", {}).get("name", "")
        
        summary = f"{home_team} vs {away_team}"
        if is_live:
            summary += " (LIVE)"
        
        description = match_data.get("field", {}).get("name", "unbekannt")
        if is_live:
            description = f"🏆 LIVE: {description}"
        
        return CalendarEvent(
            summary=summary,
            start=start,
            end=end,
            description=description,
            location=match_data.get("field", {}).get("name", "")
        )
