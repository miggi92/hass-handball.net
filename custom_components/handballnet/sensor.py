from homeassistant.helpers.entity import Entity
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_call_later
from homeassistant.core import HomeAssistant
from datetime import timedelta, datetime, timezone
from typing import Any
import logging

from .const import (
    DOMAIN,
    CONF_UPDATE_INTERVAL,
    CONF_UPDATE_INTERVAL_LIVE,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL_LIVE
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    team_id = entry.data["team_id"]
    update_interval = entry.options.get(CONF_UPDATE_INTERVAL, entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))
    live_interval = entry.options.get(CONF_UPDATE_INTERVAL_LIVE, entry.data.get(CONF_UPDATE_INTERVAL_LIVE, DEFAULT_UPDATE_INTERVAL_LIVE))

    all_sensor = HandballAllGamesSensor(hass, entry, team_id)
    heim_sensor = HandballHeimspielSensor(hass, entry, team_id)
    aus_sensor = HandballAuswaertsspielSensor(hass, entry, team_id)
    live_sensor = HandballLiveTickerSensor(hass, entry, team_id)

    async_add_entities([all_sensor, heim_sensor, aus_sensor, live_sensor])

    async def update_all(now=None):
        await all_sensor.async_update()
        all_sensor.async_write_ha_state()
        heim_sensor.async_write_ha_state()
        aus_sensor.async_write_ha_state()
        live_sensor.update_state()
        live_sensor.async_write_ha_state()
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
    def __init__(self, hass, entry, team_id):
        self.hass = hass
        self._team_id = team_id
        self._state = None
        self._attributes = {}
        self._attr_name = f"Alle Spiele {team_id}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._team_id)},
            "name": f"Handball Team {self._team_id}",
            "manufacturer": "handball.net",
            "model": "Team Kalender + Sensor",
            "entry_type": "service"
        }
        self._attr_config_entry_id = entry.entry_id

    @property
    def state(self) -> str | None:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attributes

    async def async_update(self) -> None:
        url = f"https://www.handball.net/a/sportdata/1/teams/{self._team_id}/schedule"
        try:
            session = async_get_clientsession(self.hass)
            async with session.get(url) as resp:
                if resp.status != 200:
                    _LOGGER.warning("Fehler beim Abrufen von Handball.net: %s", resp.status)
                    return
                data = await resp.json()
                matches = data.get("data", [])

                heimspiele = []
                auswaertsspiele = []
                team_name = None

                for match in matches:
                    if match["homeTeam"]["id"] == self._team_id:
                        heimspiele.append(match)
                        team_name = match["homeTeam"]["name"]
                    elif match["awayTeam"]["id"] == self._team_id:
                        auswaertsspiele.append(match)
                        team_name = match["awayTeam"]["name"]

                self._state = f"{team_name} ({len(matches)} Spiele)"
                self._attributes = {"spiele": matches}

                self.hass.data[DOMAIN][self._team_id]["matches"] = matches
                self.hass.data[DOMAIN][self._team_id]["heimspiele"] = heimspiele
                self.hass.data[DOMAIN][self._team_id]["auswaertsspiele"] = auswaertsspiele

        except Exception as e:
            _LOGGER.error("Fehler beim Abrufen der Handballdaten: %s", e)


class HandballHeimspielSensor(Entity):
    def __init__(self, hass, entry, team_id):
        self.hass = hass
        self._team_id = team_id
        self._attr_name = f"Handball Heimspiele {team_id}"
        self._attr_config_entry_id = entry.entry_id
        self._attr_device_info = {
            "identifiers": {(DOMAIN, team_id)},
            "name": f"Handball Team {team_id}",
            "manufacturer": "handball.net",
            "model": "Team Kalender + Sensor"
        }

    @property
    def state(self) -> int:
        return len(self.hass.data[DOMAIN][self._team_id].get("heimspiele", []))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"heimspiele": self.hass.data[DOMAIN][self._team_id].get("heimspiele", [])}


class HandballAuswaertsspielSensor(Entity):
    def __init__(self, hass, entry, team_id):
        self.hass = hass
        self._team_id = team_id
        self._attr_name = f"Handball Auswärtsspiele {team_id}"
        self._attr_config_entry_id = entry.entry_id
        self._attr_device_info = {
            "identifiers": {(DOMAIN, team_id)},
            "name": f"Handball Team {team_id}",
            "manufacturer": "handball.net",
            "model": "Team Kalender + Sensor"
        }

    @property
    def state(self) -> int:
        return len(self.hass.data[DOMAIN][self._team_id].get("auswaertsspiele", []))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"auswaertsspiele": self.hass.data[DOMAIN][self._team_id].get("auswaertsspiele", [])}


class HandballLiveTickerSensor(Entity):
    def __init__(self, hass, entry, team_id):
        self.hass = hass
        self._team_id = team_id
        self._attr_name = f"Liveticker aktiv {team_id}"
        self._attr_config_entry_id = entry.entry_id
        self._attr_device_info = {
            "identifiers": {(DOMAIN, team_id)},
            "name": f"Handball Team {team_id}",
            "manufacturer": "handball.net",
            "model": "Team Kalender + Sensor"
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