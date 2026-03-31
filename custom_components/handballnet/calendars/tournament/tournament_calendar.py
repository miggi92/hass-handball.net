from homeassistant.components.calendar import CalendarEvent
from datetime import datetime, timezone
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
        matches = self.hass.data.get(DOMAIN, {}).get(tournament_key, {}).get("matches", [])
        self._event = self._get_current_or_next_event(matches)
        return self._event

    async def async_update(self) -> None:
        matches = await self._async_get_tournament_matches()
        self._event = self._get_current_or_next_event(matches)

    async def _async_get_tournament_team_ids(self) -> list[str]:
        """Get all team ids that belong to the tournament."""
        tournament_key = f"tournament_{self._tournament_id}"
        tournament_data = self.hass.data.setdefault(DOMAIN, {}).setdefault(tournament_key, {})
        table_rows = tournament_data.get("table_rows", [])

        if not table_rows:
            table_data = await self._api.get_league_table(self._tournament_id)
            if isinstance(table_data, dict):
                table_rows = table_data.get("rows", [])
            elif isinstance(table_data, list):
                table_rows = table_data
            else:
                table_rows = []

        team_ids: list[str] = []
        for row in table_rows:
            if not isinstance(row, dict):
                continue

            team_id = row.get("team_id")
            if not team_id:
                team_id = row.get("team", {}).get("id")

            if team_id and team_id not in team_ids:
                team_ids.append(team_id)

        return team_ids

    async def _async_get_tournament_matches(self) -> list[dict]:
        """Fetch, deduplicate and cache all tournament matches."""
        team_ids = await self._async_get_tournament_team_ids()
        if not team_ids:
            return []

        unique_matches: dict[str, dict] = {}
        for team_id in team_ids:
            try:
                matches = await self._api.get_team_schedule(team_id)
            except Exception as err:
                _LOGGER.debug("Could not get matches for team %s: %s", team_id, err)
                continue

            if not matches:
                continue

            for match in matches:
                match_id = match.get("id")
                if not match_id or match_id in unique_matches:
                    continue

                home_team_id = match.get("homeTeam", {}).get("id")
                away_team_id = match.get("awayTeam", {}).get("id")
                if home_team_id in team_ids and away_team_id in team_ids:
                    unique_matches[match_id] = match

        matches = sorted(unique_matches.values(), key=lambda item: item.get("startsAt", 0))

        tournament_key = f"tournament_{self._tournament_id}"
        tournament_data = self.hass.data.setdefault(DOMAIN, {}).setdefault(tournament_key, {})
        tournament_data["matches"] = matches

        return matches

    async def async_get_events(self, hass, start_date: datetime, end_date: datetime) -> list[CalendarEvent]:
        matches = await self._async_get_tournament_matches()
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
        
        # Sort events by start time
        events.sort(key=lambda x: x.start)
        return events
