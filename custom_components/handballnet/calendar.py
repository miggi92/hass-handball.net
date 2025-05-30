from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from datetime import datetime, timedelta, timezone
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    team_id = entry.data["team_id"]
    entity = HandballCalendar(hass, entry, team_id)
    
    # Add calendar to sensors list for logo updates
    if "sensors" not in hass.data[DOMAIN][team_id]:
        hass.data[DOMAIN][team_id]["sensors"] = []
    hass.data[DOMAIN][team_id]["sensors"].append(entity)
    
    async_add_entities([entity], update_before_add=True)

class HandballCalendar(CalendarEntity):
    def __init__(self, hass, entry, team_id):
        self.hass = hass
        self._team_id = team_id
        
        # Use team name from config if available, fallback to team_id
        team_name = entry.data.get("team_name", team_id)
        self._attr_name = f"Spielplan {team_name}"
        self._attr_unique_id = f"handball_calendar_{team_id}"
        self._attr_config_entry_id = entry.entry_id
        self._attr_device_info = {
            "identifiers": {(DOMAIN, team_id)},
            "name": f"Handball {team_name}",
            "manufacturer": "handball.net",
            "model": "Handball Team",
            "entry_type": "service"
        }
        self._event = None

    def update_device_name(self, team_name: str) -> None:
        """Update device name with actual team name"""
        if team_name and team_name != "":
            self._attr_device_info["name"] = f"Handball {team_name}"

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
                return CalendarEvent(
                    summary=f"{match['homeTeam']['name']} vs {match['awayTeam']['name']} (LIVE)",
                    start=start,
                    end=end,
                    description=f"🏆 LIVE: {match.get('field', {}).get('name', 'unbekannt')}",
                    location=match.get("field", {}).get("name", "")
                )
        
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
                return CalendarEvent(
                    summary=f"{match['homeTeam']['name']} vs {match['awayTeam']['name']}",
                    start=start,
                    end=start + timedelta(hours=2),
                    description=match.get("field", {}).get("name", "unbekannt"),
                    location=match.get("field", {}).get("name", "")
                )
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
                summary = f"{match['homeTeam']['name']} vs {match['awayTeam']['name']}"
                if is_live:
                    summary += " (LIVE)"
                
                description = match.get("field", {}).get("name", "unbekannt")
                if is_live:
                    description = f"🏆 LIVE: {description}"
                
                events.append(CalendarEvent(
                    summary=summary,
                    start=start,
                    end=end,
                    description=description,
                    location=match.get("field", {}).get("name", "")
                ))
        return events