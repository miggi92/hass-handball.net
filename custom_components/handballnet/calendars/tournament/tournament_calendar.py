from homeassistant.components.calendar import CalendarEvent
from datetime import datetime, timezone, timedelta
from .base_calendar import HandballBaseCalendar
from ...const import DOMAIN
from ...api import HandballNetAPI
import logging

_LOGGER = logging.getLogger(__name__)

class HandballTournamentCalendar(HandballBaseCalendar):
    def __init__(self, hass, entry, tournament_id, api: HandballNetAPI):
        super().__init__(hass, entry, tournament_id)
        self._api = api
        
        # Use tournament name from config if available, fallback to tournament_id
        tournament_name = entry.data.get("tournament_name", tournament_id)
        self._attr_name = f"{tournament_name} Spielplan"
        self._attr_unique_id = f"handball_tournament_{tournament_id}_calendar"
        self._event = None

    @property
    def event(self) -> CalendarEvent | None:
        tournament_key = f"tournament_{self._tournament_id}"
        table_rows = self.hass.data.get(DOMAIN, {}).get(tournament_key, {}).get("table_rows", [])
        
        if not table_rows:
            return None
            
        # Get all team IDs from tournament
        team_ids = [row.get("team_id") for row in table_rows if row.get("team_id")]
        
        # Since this is a property, we can't use async here
        # We'll need to implement this differently or return None for now
        # The main calendar events will be provided by async_get_events
        return None

    async def async_get_events(self, hass, start_date: datetime, end_date: datetime) -> list[CalendarEvent]:
        tournament_key = f"tournament_{self._tournament_id}"
        table_rows = self.hass.data.get(DOMAIN, {}).get(tournament_key, {}).get("table_rows", [])
        
        if not table_rows:
            return []
            
        # Get all team IDs from tournament
        team_ids = [row.get("team_id") for row in table_rows if row.get("team_id")]
        
        # Collect all matches from tournament teams with deduplication
        unique_matches = {}  # Use dict to deduplicate by match ID
        for team_id in team_ids:
            try:
                matches = await self._api.get_team_schedule(team_id)
                if matches:
                    for match in matches:
                        match_id = match.get("id")
                        if match_id and match_id not in unique_matches:
                            # Only add matches where both teams are in this tournament
                            home_team_id = match.get("homeTeam", {}).get("id")
                            away_team_id = match.get("awayTeam", {}).get("id")
                            
                            if home_team_id in team_ids and away_team_id in team_ids:
                                unique_matches[match_id] = match
            except Exception as e:
                _LOGGER.debug("Could not get matches for team %s: %s", team_id, e)
        
        events: list[CalendarEvent] = []
        now = datetime.now(timezone.utc)
        
        for match in unique_matches.values():
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
        
        # Sort events by start time
        events.sort(key=lambda x: x.start)
        return events
