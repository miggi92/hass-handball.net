from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_call_later
from homeassistant.core import HomeAssistant
from datetime import datetime, timezone
from typing import Any
import logging

from .const import (
    DOMAIN,
    CONF_UPDATE_INTERVAL,
    CONF_UPDATE_INTERVAL_LIVE,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL_LIVE
)
from .api import HandballNetAPI

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    team_id = entry.data["team_id"]
    update_interval = entry.options.get(CONF_UPDATE_INTERVAL, entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))
    live_interval = entry.options.get(CONF_UPDATE_INTERVAL_LIVE, entry.data.get(CONF_UPDATE_INTERVAL_LIVE, DEFAULT_UPDATE_INTERVAL_LIVE))

    api = HandballNetAPI(hass)
    
    all_sensor = HandballAllGamesSensor(hass, entry, team_id, api)
    heim_sensor = HandballHeimspielSensor(hass, entry, team_id)
    aus_sensor = HandballAuswaertsspielSensor(hass, entry, team_id)
    live_sensor = HandballLiveTickerSensor(hass, entry, team_id)
    table_sensor = HandballTablePositionSensor(hass, entry, team_id, api)

    async_add_entities([all_sensor, heim_sensor, aus_sensor, live_sensor, table_sensor])

    async def update_all(now=None):
        await all_sensor.async_update()
        await table_sensor.async_update()
        all_sensor.async_write_ha_state()
        heim_sensor.async_write_ha_state()
        aus_sensor.async_write_ha_state()
        live_sensor.update_state()
        live_sensor.async_write_ha_state()
        table_sensor.async_write_ha_state()
        await schedule_next_poll()

    async def schedule_next_poll():
        now_ts = datetime.now(timezone.utc).timestamp()
        matches = hass.data.get(DOMAIN, {}).get(team_id, {}).get("matches", [])
        is_live = any(
            match.get("startsAt", 0) / 1000 <= now_ts <= match.get("startsAt", 0) / 1000 + 7200
            for match in matches
        )
        interval = live_interval if is_live else update_interval
        async_call_later(hass, interval, update_all)

    await update_all()


class HandballAllGamesSensor(Entity):
    def __init__(self, hass, entry, team_id, api: HandballNetAPI):
        self.hass = hass
        self._team_id = team_id
        self._api = api
        self._state = None
        self._attributes = {}
        self._attr_name = f"Alle Spiele {team_id}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._team_id)},
            "name": f"Handball Team {self._team_id}",
            "manufacturer": "handball.net",
            "model": "Handball Team",
            "entry_type": "service"
        }
        self._attr_config_entry_id = entry.entry_id
        self._attr_unique_id = f"handball_all_games_{team_id}"

    @property
    def state(self) -> str | None:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attributes

    async def async_update(self) -> None:
        matches = await self._api.get_team_schedule(self._team_id)
        if matches is None:
            return

        heimspiele = []
        auswaertsspiele = []
        team_name = None
        next_match = None
        last_match = None
        now = datetime.now(timezone.utc)

        for match in matches:
            if match["homeTeam"]["id"] == self._team_id:
                heimspiele.append(match)
                team_name = match["homeTeam"]["name"]
            elif match["awayTeam"]["id"] == self._team_id:
                auswaertsspiele.append(match)
                team_name = match["awayTeam"]["name"]

        # Find next and last match
        for match in sorted(matches, key=lambda x: x.get("startsAt", 0)):
            match_time = datetime.fromtimestamp(match.get("startsAt", 0) / 1000, tz=timezone.utc)
            if match_time > now and next_match is None:
                next_match = {
                    "id": match.get("id"),
                    "home_team": match.get("homeTeam", {}).get("name"),
                    "away_team": match.get("awayTeam", {}).get("name"),
                    "starts_at": match.get("startsAt"),
                    "field": match.get("field", {}).get("name")
                }
            elif match_time <= now:
                last_match = {
                    "id": match.get("id"),
                    "home_team": match.get("homeTeam", {}).get("name"),
                    "away_team": match.get("awayTeam", {}).get("name"),
                    "starts_at": match.get("startsAt"),
                    "home_goals": match.get("homeGoals"),
                    "away_goals": match.get("awayGoals"),
                    "state": match.get("state")
                }

        self._state = f"{team_name} ({len(matches)} Spiele)"
        self._attributes = {
            "team_name": team_name,
            "total_games": len(matches),
            "home_games": len(heimspiele),
            "away_games": len(auswaertsspiele),
            "next_match": next_match,
            "last_match": last_match
        }

        self.hass.data[DOMAIN][self._team_id]["matches"] = matches
        self.hass.data[DOMAIN][self._team_id]["heimspiele"] = heimspiele
        self.hass.data[DOMAIN][self._team_id]["auswaertsspiele"] = auswaertsspiele


class HandballHeimspielSensor(Entity):
    def __init__(self, hass, entry, team_id):
        self.hass = hass
        self._team_id = team_id
        self._attr_name = f"Handball Heimspiele {team_id}"
        self._attr_config_entry_id = entry.entry_id
        self._attr_unique_id = f"handball_home_games_{team_id}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._team_id)},
            "name": f"Handball Team {team_id}",
            "manufacturer": "handball.net",
            "model": "Handball Team"
        }

    @property
    def state(self) -> int:
        return len(self.hass.data[DOMAIN][self._team_id].get("heimspiele", []))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        heimspiele = self.hass.data[DOMAIN][self._team_id].get("heimspiele", [])
        next_home_match = None
        now = datetime.now(timezone.utc)
        
        for match in sorted(heimspiele, key=lambda x: x.get("startsAt", 0)):
            match_time = datetime.fromtimestamp(match.get("startsAt", 0) / 1000, tz=timezone.utc)
            if match_time > now:
                next_home_match = {
                    "opponent": match.get("awayTeam", {}).get("name"),
                    "starts_at": match.get("startsAt"),
                    "field": match.get("field", {}).get("name")
                }
                break
        
        return {
            "total_home_games": len(heimspiele),
            "next_home_match": next_home_match
        }


class HandballAuswaertsspielSensor(Entity):
    def __init__(self, hass, entry, team_id):
        self.hass = hass
        self._team_id = team_id
        self._attr_name = f"Handball Auswärtsspiele {team_id}"
        self._attr_config_entry_id = entry.entry_id
        self._attr_unique_id = f"handball_away_games_{team_id}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._team_id)},
            "name": f"Handball Team {team_id}",
            "manufacturer": "handball.net",
            "model": "Handball Team"
        }

    @property
    def state(self) -> int:
        return len(self.hass.data[DOMAIN][self._team_id].get("auswaertsspiele", []))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        auswaertsspiele = self.hass.data[DOMAIN][self._team_id].get("auswaertsspiele", [])
        next_away_match = None
        now = datetime.now(timezone.utc)
        
        for match in sorted(auswaertsspiele, key=lambda x: x.get("startsAt", 0)):
            match_time = datetime.fromtimestamp(match.get("startsAt", 0) / 1000, tz=timezone.utc)
            if match_time > now:
                next_away_match = {
                    "opponent": match.get("homeTeam", {}).get("name"),
                    "starts_at": match.get("startsAt"),
                    "field": match.get("field", {}).get("name")
                }
                break
        
        return {
            "total_away_games": len(auswaertsspiele),
            "next_away_match": next_away_match
        }


class HandballLiveTickerSensor(Entity):
    def __init__(self, hass, entry, team_id):
        self.hass = hass
        self._team_id = team_id
        self._attr_name = f"Liveticker aktiv {self._team_id}"
        self._attr_unique_id = f"handball_live_ticker_{team_id}"
        self._attr_config_entry_id = entry.entry_id
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._team_id)},
            "name": f"Handball Team {self._team_id}",
            "manufacturer": "handball.net",
            "model": "Handball Team"
        }
        self._attr_icon = "mdi:clock-alert"
        self._attr_should_poll = False
        self._attr_native_value = "off"

    def update_state(self) -> None:
        now_ts = datetime.now(timezone.utc).timestamp()
        matches = self.hass.data.get(DOMAIN, {}).get(self._team_id, {}).get("matches", [])
        self._attr_native_value = "on" if any(
            match.get("startsAt", 0) / 1000 <= now_ts <= match.get("startsAt", 0) / 1000 + 7200
            for match in matches
        ) else "off"

    @property
    def state(self) -> str:
        return self._attr_native_value

    @property
    def is_on(self) -> bool:
        return self._attr_native_value == "on"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "team_id": self._team_id,
            "matches_tracked": len(self.hass.data.get(DOMAIN, {}).get(self._team_id, {}).get("matches", []))
        }


class HandballTablePositionSensor(Entity):
    def __init__(self, hass, entry, team_id, api: HandballNetAPI):
        self.hass = hass
        self._team_id = team_id
        self._api = api
        self._state = None
        self._attributes = {}
        self._tournament_id = None
        self._attr_name = f"Handball Tabellenplatz {team_id}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._team_id)},
            "name": f"Handball Team {self._team_id}",
            "manufacturer": "handball.net",
            "model": "Handball Team",
            "entry_type": "service"
        }
        self._attr_config_entry_id = entry.entry_id
        self._attr_unique_id = f"handball_table_position_{team_id}"
        self._attr_icon = "mdi:trophy"

    @property
    def state(self) -> int | None:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attributes

    async def async_update(self) -> None:
        # Get tournament ID from matches
        matches = self.hass.data.get(DOMAIN, {}).get(self._team_id, {}).get("matches", [])
        if not matches:
            return

        # Extract tournament ID from first match
        tournament_id = matches[0].get("tournament", {}).get("id")
        if not tournament_id:
            return

        self._tournament_id = tournament_id

        # Get table position
        table_position = await self._api.get_team_table_position(self._team_id, tournament_id)
        if table_position is None:
            return

        self._state = table_position["position"]
        self._attributes = {
            "tournament_id": tournament_id,
            "tournament_name": matches[0].get("tournament", {}).get("name", ""),
            "team_name": table_position["team_name"],
            "points": table_position["points"],
            "games_played": table_position["games_played"],
            "wins": table_position["wins"],
            "draws": table_position["draws"],
            "losses": table_position["losses"],
            "goals_scored": table_position["goals_scored"],
            "goals_conceded": table_position["goals_conceded"],
            "goal_difference": table_position["goal_difference"]
        }