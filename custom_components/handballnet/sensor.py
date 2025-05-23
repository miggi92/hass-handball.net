from homeassistant.helpers.entity import Entity
import logging
import aiohttp
from datetime import datetime
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class HandballNetSensor(Entity):
    def __init__(self, hass, team_id):
        self.hass = hass
        self._team_id = team_id
        self._state = None
        self._attributes = {}
        self._name = f"Handball Team {team_id}"

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return self._attributes

    async def async_update(self):
        url = f"https://www.handball.net/a/sportdata/1/teams/{self._team_id}/schedule"
        try:
            session = self.hass.helpers.aiohttp_client.async_get_clientsession()
            async with session.get(url) as resp:
                if resp.status != 200:
                    _LOGGER.warning("Fehler beim Abrufen von Handball.net: %s", resp.status)
                    return
                data = await resp.json()
                matches = data.get("data", [])
                team_name = matches[0]["homeTeam"]["name"] if matches else "Unbekannt"

                self._state = f"{team_name} ({len(matches)} Spiele)"
                self._attributes = {
                    "spiele": matches
                }

                # Gemeinsame Daten aktualisieren
                self.hass.data[DOMAIN][self._team_id]["matches"] = matches

        except Exception as e:
            _LOGGER.error("Fehler beim Abrufen der Handballdaten: %s", e)
