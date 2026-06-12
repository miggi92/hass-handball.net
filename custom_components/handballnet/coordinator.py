from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import HandballNetAPI
from .const import (
    CONF_ENTITY_TYPE,
    CONF_TEAM_ID,
    CONF_TEAM_MAPPING,
    CONF_TOURNAMENT_ID,
    CONF_UPDATE_INTERVAL,
    CONF_UPDATE_INTERVAL_LIVE,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL_LIVE,
    DOMAIN,
    HEALTH_CHECK_STALE_HOURS,
    ENTITY_TYPE_CLUB,
    ENTITY_TYPE_TEAM,
    ENTITY_TYPE_TOURNAMENT,
)
from .utils import HandballNetUtils

_LOGGER = logging.getLogger(__name__)


class HandballDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry) -> None:
        self._entry = entry
        self._api = HandballNetAPI(hass)
        self._utils = HandballNetUtils()
        self._entity_type = entry.data.get(CONF_ENTITY_TYPE, ENTITY_TYPE_TEAM)
        self._standard_interval = timedelta(
            seconds=entry.options.get(CONF_UPDATE_INTERVAL, entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))
        )
        self._live_interval = timedelta(
            seconds=entry.options.get(CONF_UPDATE_INTERVAL_LIVE, entry.data.get(CONF_UPDATE_INTERVAL_LIVE, DEFAULT_UPDATE_INTERVAL_LIVE))
        )
        self._team_items = self._build_team_items(entry)
        self._tournament_id = entry.data.get(CONF_TOURNAMENT_ID)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=self._standard_interval,
        )

    def _build_team_items(self, entry) -> list[tuple[str, str]]:
        if self._entity_type == ENTITY_TYPE_CLUB:
            return list(entry.data.get(CONF_TEAM_MAPPING, {}).items())

        if self._entity_type == ENTITY_TYPE_TEAM:
            team_id = entry.data.get(CONF_TEAM_ID)
            if not team_id:
                return []
            return [(team_id, entry.data.get("team_name", team_id))]

        return []

    async def _async_update_data(self) -> dict[str, Any]:
        if self._entity_type == ENTITY_TYPE_TOURNAMENT:
            return await self._async_update_tournament_data()

        team_results = await asyncio.gather(
            *(self._load_team_bucket(team_id, team_name) for team_id, team_name in self._team_items),
            return_exceptions=True,
        )

        teams: dict[str, dict[str, Any]] = {}
        is_live = False

        for (team_id, team_name), result in zip(self._team_items, team_results, strict=False):
            if isinstance(result, Exception):
                _LOGGER.error("Error updating team %s: %s", team_id, result)
                team_bucket = self._create_error_team_bucket(team_id, team_name, str(result))
            else:
                team_bucket = result

            teams[team_id] = team_bucket
            is_live = is_live or bool(team_bucket.get("is_live"))

        self.update_interval = self._live_interval if is_live else self._standard_interval

        for team_id, team_bucket in teams.items():
            self._store_team_bucket(team_id, team_bucket)

        return {
            "entity_type": self._entity_type,
            "teams": teams,
            "tournament": None,
            "is_live": is_live,
        }

    async def _async_update_tournament_data(self) -> dict[str, Any]:
        if not self._tournament_id:
            raise UpdateFailed("Tournament ID is missing")

        table_data = await self._api.get_league_table(self._tournament_id)
        if not table_data:
            tournament_bucket = {
                "tournament_id": self._tournament_id,
                "tournament_info": {"name": self._tournament_id, "acronym": "", "organization": "", "logo": ""},
                "table_rows": [],
                "team_positions": {},
                "matches": [],
            }
            self._store_tournament_bucket(tournament_bucket)
            return {"entity_type": self._entity_type, "teams": {}, "tournament": tournament_bucket, "is_live": False}

        tournament_info = await self._get_tournament_info()
        table_rows = await self._extract_table_rows_with_logos(table_data)
        matches = await self._fetch_tournament_matches(table_rows)
        team_positions = {row.get("team_id"): row for row in table_rows if row.get("team_id")}

        tournament_bucket = {
            "tournament_id": self._tournament_id,
            "tournament_info": tournament_info,
            "table_rows": table_rows,
            "team_positions": team_positions,
            "matches": matches,
        }

        self._store_tournament_bucket(tournament_bucket)
        return {"entity_type": self._entity_type, "teams": {}, "tournament": tournament_bucket, "is_live": False}

    async def _load_team_bucket(self, team_id: str, team_name: str) -> dict[str, Any]:
        matches = await self._api.get_team_schedule(team_id) or []
        essential_matches = self._extract_essential_match_data(team_id, matches)

        team_info = None
        try:
            team_info = await self._api.get_team_info(team_id)
        except Exception as err:
            _LOGGER.debug("Could not fetch team info for %s: %s", team_id, err)

        if team_info and team_info.get("logo"):
            team_logo_url = team_info.get("logo")
        else:
            team_logo_url = self._api.extract_team_logo_url(matches, team_id)

        if team_info and team_info.get("name"):
            team_name = team_info.get("name")

        live_matches = self._get_live_matches(essential_matches)
        live_events = await self._load_live_events(live_matches)
        tournament_id = self._find_tournament_id(essential_matches, team_info)
        table_position = await self._load_table_position(team_id, tournament_id)
        health = self._build_health_data(essential_matches)
        next_match = self._get_next_match(essential_matches)
        last_match = self._get_last_match(essential_matches)

        return {
            "team_id": team_id,
            "configured_team_name": team_name,
            "team_name": team_name,
            "team_info": team_info,
            "team_logo_url": team_logo_url,
            "matches": essential_matches,
            "next_match": next_match,
            "last_match": last_match,
            "live_matches": live_matches,
            "live_events": live_events,
            "tournament_id": tournament_id,
            "table_position": table_position,
            "health": health,
            "is_live": bool(live_matches),
        }

    def _create_error_team_bucket(self, team_id: str, team_name: str, error: str) -> dict[str, Any]:
        return {
            "team_id": team_id,
            "configured_team_name": team_name,
            "team_name": team_name,
            "team_info": None,
            "team_logo_url": None,
            "matches": [],
            "next_match": None,
            "last_match": None,
            "live_matches": [],
            "live_events": {},
            "tournament_id": None,
            "table_position": None,
            "health": {"state": "error", "attributes": {}, "error": error},
            "is_live": False,
            "error": error,
        }

    async def _load_live_events(self, live_matches: list[dict[str, Any]]) -> dict[str, Any]:
        if not live_matches:
            return {}

        game_id = live_matches[0].get("id")
        if not game_id:
            return {}

        live_ticker = await self._api.get_live_ticker(game_id)
        if not live_ticker:
            return {"game_id": game_id, "events": [], "total_events": 0, "last_update": datetime.now(timezone.utc).isoformat()}

        events = live_ticker.get("events", [])
        return {
            "game_id": game_id,
            "events": events,
            "total_events": len(events),
            "last_update": datetime.now(timezone.utc).isoformat(),
        }

    async def _load_table_position(self, team_id: str, tournament_id: str | None) -> dict[str, Any] | None:
        if not tournament_id:
            return None

        try:
            return await self._api.get_team_table_position(team_id, tournament_id)
        except Exception as err:
            _LOGGER.debug("Could not fetch table position for %s: %s", team_id, err)
            return None

    def _extract_essential_match_data(self, team_id: str, matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
        essential_matches: list[dict[str, Any]] = []

        for match in matches:
            home_logo = match.get("homeTeam", {}).get("logo")
            away_logo = match.get("awayTeam", {}).get("logo")

            essential_matches.append({
                "id": match.get("id"),
                "startsAt": match.get("startsAt"),
                "state": match.get("state"),
                "homeTeam": {
                    "id": match.get("homeTeam", {}).get("id"),
                    "name": match.get("homeTeam", {}).get("name"),
                    "logo": self._utils.normalize_logo_url(home_logo) if home_logo else None,
                },
                "awayTeam": {
                    "id": match.get("awayTeam", {}).get("id"),
                    "name": match.get("awayTeam", {}).get("name"),
                    "logo": self._utils.normalize_logo_url(away_logo) if away_logo else None,
                },
                "field": {"name": match.get("field", {}).get("name")},
                "homeGoals": match.get("homeGoals"),
                "awayGoals": match.get("awayGoals"),
                "tournament": {
                    "id": match.get("tournament", {}).get("id"),
                    "name": match.get("tournament", {}).get("name"),
                },
                "isHomeMatch": match.get("homeTeam", {}).get("id") == team_id,
                "isAway": match.get("awayTeam", {}).get("id") == team_id,
                "lastUpdated": match.get("lastUpdated"),
                "status": match.get("status"),
                "error": match.get("error"),
            })

        return essential_matches

    def _get_live_matches(self, matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
        now_ts = datetime.now(timezone.utc).timestamp()
        return [
            match
            for match in matches
            if match.get("startsAt", 0) / 1000 <= now_ts <= match.get("startsAt", 0) / 1000 + 7200
        ]

    def _get_next_match(self, matches: list[dict[str, Any]]) -> dict[str, Any] | None:
        now = datetime.now(timezone.utc)
        for match in sorted(matches, key=lambda item: item.get("startsAt", 0)):
            start_ts = match.get("startsAt")
            if not isinstance(start_ts, int):
                continue
            start = datetime.fromtimestamp(start_ts / 1000, tz=timezone.utc)
            if start > now:
                return self._create_match_info(match, include_result=False)
        return None

    def _get_last_match(self, matches: list[dict[str, Any]]) -> dict[str, Any] | None:
        now = datetime.now(timezone.utc)
        last_match = None
        for match in matches:
            start_ts = match.get("startsAt")
            if not isinstance(start_ts, int):
                continue
            start = datetime.fromtimestamp(start_ts / 1000, tz=timezone.utc)
            if start <= now:
                last_match = self._create_match_info(match, include_result=True)
        return last_match

    def _create_match_info(self, match: dict[str, Any], include_result: bool = False) -> dict[str, Any]:
        start_ts = match.get("startsAt")
        start = datetime.fromtimestamp(start_ts / 1000, tz=timezone.utc)
        time_formats = self._utils.format_datetime_for_display(start)
        home_team = self._team_info(match.get("homeTeam", {}))
        away_team = self._team_info(match.get("awayTeam", {}))
        opponent = away_team if match.get("isHomeMatch") else home_team

        match_info = {
            "id": match.get("id"),
            "home_team": home_team,
            "away_team": away_team,
            "opponent": opponent,
            "is_home": match.get("isHomeMatch", False),
            "starts_at": match.get("startsAt"),
            "starts_at_formatted": time_formats["formatted"],
            "starts_at_local": time_formats["local"],
            "field": match.get("field", {}).get("name"),
        }

        if include_result:
            match_info.update({
                "home_goals": match.get("homeGoals"),
                "away_goals": match.get("awayGoals"),
                "state": match.get("state"),
            })

        return match_info

    def _team_info(self, team_data: dict[str, Any]) -> dict[str, Any]:
        logo_url = team_data.get("logo")
        return {
            "id": team_data.get("id"),
            "name": team_data.get("name", ""),
            "logo": self._utils.normalize_logo_url(logo_url) if logo_url else None,
        }

    def _build_health_data(self, matches: list[dict[str, Any]]) -> dict[str, Any]:
        if not matches:
            return {"state": "unknown", "attributes": {}}

        now = datetime.now(timezone.utc)
        stale_threshold = now - timedelta(hours=HEALTH_CHECK_STALE_HOURS)

        if all(
            datetime.fromtimestamp((match.get("lastUpdated", 0) or 0) / 1000, tz=timezone.utc) < stale_threshold
            for match in matches
        ):
            return {"state": "stale", "attributes": {}}

        if any(match.get("error") for match in matches):
            return {"state": "error", "attributes": {}}

        if any(match.get("status") == "unhealthy" for match in matches):
            return {"state": "unhealthy", "attributes": {}}

        if any(match.get("status") == "degraded" for match in matches):
            return {"state": "degraded", "attributes": {}}

        return {
            "state": "healthy",
            "attributes": {
                "last_updated": max(match.get("lastUpdated", 0) for match in matches),
                "total_matches": len(matches),
                "healthy_matches": sum(1 for match in matches if match.get("status") == "healthy"),
                "degraded_matches": sum(1 for match in matches if match.get("status") == "degraded"),
                "unhealthy_matches": sum(1 for match in matches if match.get("status") == "unhealthy"),
                "stale_matches": sum(
                    1
                    for match in matches
                    if datetime.fromtimestamp((match.get("lastUpdated", 0) or 0) / 1000, tz=timezone.utc) < stale_threshold
                ),
            },
        }

    async def _get_tournament_info(self) -> dict[str, Any]:
        data = await self._api._make_request(f"tournaments/{self._tournament_id}/table")
        if data and "data" in data:
            tournament_data = data["data"].get("tournament", {})
            return {
                "name": tournament_data.get("name", self._tournament_id),
                "acronym": tournament_data.get("acronym", ""),
                "organization": tournament_data.get("organization", {}).get("name", ""),
                "logo": tournament_data.get("logo", ""),
            }
        return {"name": self._tournament_id, "acronym": "", "organization": "", "logo": ""}

    async def _extract_table_rows_with_logos(self, table_data: Any) -> list[dict[str, Any]]:
        if isinstance(table_data, dict):
            rows = table_data.get("rows", [])
        elif isinstance(table_data, list):
            rows = table_data
        else:
            return []

        formatted_rows: list[dict[str, Any]] = []
        total_teams = len(rows)

        for row in rows:
            if not isinstance(row, dict):
                continue

            team_info = row.get("team", {})
            team_id = team_info.get("id")
            team_logo = None

            if team_id:
                try:
                    team_data = await self._api.get_team_info(team_id)
                    if team_data and team_data.get("logo"):
                        team_logo = team_data.get("logo")
                except Exception as err:
                    _LOGGER.debug("Could not fetch logo for team %s: %s", team_id, err)

            if not team_logo:
                team_logo = team_info.get("logo")

            position = row.get("rank", 0)
            formatted_rows.append({
                "position": position,
                "team_id": team_id,
                "team_name": team_info.get("name", ""),
                "team_acronym": team_info.get("acronym", ""),
                "team_logo": self._utils.normalize_logo_url(team_logo) if team_logo else None,
                "points": row.get("points", "0:0"),
                "games_played": row.get("games", 0),
                "wins": row.get("wins", 0),
                "draws": row.get("draws", 0),
                "losses": row.get("losses", 0),
                "goals_scored": row.get("goals", 0),
                "goals_conceded": row.get("goalsAgainst", 0),
                "goal_difference": row.get("goalDifference", 0),
                "promoted": row.get("promoted"),
                "relegated": row.get("relegated"),
                "is_last_place": position == total_teams,
            })

        return formatted_rows

    async def _fetch_tournament_matches(self, table_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        team_ids = [row.get("team_id") for row in table_rows if row.get("team_id")]
        if not team_ids:
            return []

        unique_matches: dict[str, dict[str, Any]] = {}
        schedule_results = await asyncio.gather(
            *(self._api.get_team_schedule(team_id) for team_id in team_ids),
            return_exceptions=True,
        )

        for team_id, matches_result in zip(team_ids, schedule_results, strict=False):
            if isinstance(matches_result, Exception):
                _LOGGER.debug("Could not get tournament matches for team %s: %s", team_id, matches_result)
                continue

            for match in matches_result or []:
                match_id = match.get("id")
                if not match_id or match_id in unique_matches:
                    continue

                home_team_id = match.get("homeTeam", {}).get("id")
                away_team_id = match.get("awayTeam", {}).get("id")
                if home_team_id in team_ids and away_team_id in team_ids:
                    unique_matches[match_id] = match

        return self._extract_essential_match_data("", sorted(unique_matches.values(), key=lambda item: item.get("startsAt", 0)))

    def _store_team_bucket(self, team_id: str, team_bucket: dict[str, Any]) -> None:
        domain_data = self.hass.data.setdefault(DOMAIN, {})
        bucket = domain_data.setdefault(team_id, {})
        sensors = bucket.get("sensors", [])
        bucket.update({
            "matches": team_bucket.get("matches", []),
            "team_name": team_bucket.get("team_name"),
            "team_logo_url": team_bucket.get("team_logo_url"),
            "table_position": team_bucket.get("table_position"),
            "live_events": team_bucket.get("live_events", {}),
            "live_matches": team_bucket.get("live_matches", []),
            "next_match": team_bucket.get("next_match"),
            "last_match": team_bucket.get("last_match"),
            "tournament_id": team_bucket.get("tournament_id"),
            "health": team_bucket.get("health", {}),
            "sensors": sensors,
        })

    def _store_tournament_bucket(self, tournament_bucket: dict[str, Any]) -> None:
        domain_data = self.hass.data.setdefault(DOMAIN, {})
        tournament_key = f"tournament_{self._tournament_id}"
        bucket = domain_data.setdefault(tournament_key, {"sensors": []})
        bucket.update({
            "tournament_info": tournament_bucket.get("tournament_info", {}),
            "table_rows": tournament_bucket.get("table_rows", []),
            "team_positions": tournament_bucket.get("team_positions", {}),
            "matches": tournament_bucket.get("matches", []),
            "sensors": bucket.get("sensors", []),
        })