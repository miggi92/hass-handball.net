from homeassistant.helpers.entity import Entity
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_interval
from datetime import timedelta
import logging
from .const import DOMAIN, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    team_id = entry.data["team_id"]
    update_interval = entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
    all_sensor = HandballAllGamesSensor(hass, entry, team_id)
    heim_sensor = HandballHeimspielSensor(hass, entry, team_id)
    aus_sensor = HandballAuswaertsspielSensor(hass, entry, team_id)
    async_add_entities([all_sensor, heim_sensor, aus_sensor], update_before_add=True)

    async def update_all(now):
        await all_sensor.async_update()
        all_sensor.async_write_ha_state()
        heim_sensor.async_write_ha_state()
        aus_sensor.async_write_ha_state()

    async_track_time_interval(hass, update_all, timedelta(seconds=update_interval))

class HandballAllGamesSensor(Entity):
    def __init__(self, hass, entry, team_id):
        self.hass = hass
        self._team_id = team_id
        self._state = None
        self._attributes = {}
        self._attr_name = f"Alle Spiele {team_id}"
        self._attr_unique_id = f"handball_allgames_{team_id}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._team_id)},
            "name": f"Handball Team {self._team_id}",
            "manufacturer": "handball.net",
            "model": "Team Kalender + Sensor",
            "entry_type": "service"
        }
        self._attr_config_entry_id = entry.entry_id

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return self._attributes

    async def async_update(self):
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
        self._attr_unique_id = f"handball_heim_{team_id}"
        self._attr_config_entry_id = entry.entry_id
        self._attr_device_info = {
            "identifiers": {(DOMAIN, team_id)},
            "name": f"Handball Team {team_id}",
            "manufacturer": "handball.net",
            "model": "Team Kalender + Sensor"
        }

    @property
    def state(self):
        return len(self.hass.data[DOMAIN][self._team_id].get("heimspiele", []))

    @property
    def extra_state_attributes(self):
        return {"heimspiele": self.hass.data[DOMAIN][self._team_id].get("heimspiele", [])}

class HandballAuswaertsspielSensor(Entity):
    def __init__(self, hass, entry, team_id):
        self.hass = hass
        self._team_id = team_id
        self._attr_name = f"Handball Auswärtsspiele {team_id}"
        self._attr_unique_id = f"handball_auswaerts_{team_id}"
        self._attr_config_entry_id = entry.entry_id
        self._attr_device_info = {
            "identifiers": {(DOMAIN, team_id)},
            "name": f"Handball Team {team_id}",
            "manufacturer": "handball.net",
            "model": "Team Kalender + Sensor"
        }

    @property
    def state(self):
        return len(self.hass.data[DOMAIN][self._team_id].get("auswaertsspiele", []))

    @property
    def extra_state_attributes(self):
        return {"auswaertsspiele": self.hass.data[DOMAIN][self._team_id].get("auswaertsspiele", [])}