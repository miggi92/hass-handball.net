from homeassistant.helpers.entity import Entity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import AddEntitiesCallback

import requests
import datetime
import logging

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    _LOGGER.info("Sensor wird erstellt")
    team_id = entry.data["team_id"]
    async_add_entities([HandballNetSensor(team_id)], update_before_add=True)

class HandballNetSensor(Entity):
    def __init__(self, team_id):
        self._team_id = team_id
        self._state = None
        self._attributes = {}

    def update(self):
        _LOGGER.info("Update aufgerufen für Team %s", self._team_id)
        try:
            url = f"https://www.handball.net/a/sportdata/1/teams/{self._team_id}/schedule"
            response = requests.get(url)
            data = response.json()
            matches = data.get("data", [])
            team_name = matches[0]["homeTeam"]["name"] if matches else "Unbekannt"
            self._state = f"{team_name}: {len(matches)} Spiele"
            self._attributes = {
                "anzahl_spiele": len(matches),
            }
        except Exception as e:
            self._state = "Fehler"
            self._attributes = {"error": str(e)}

    @property
    def name(self):
        return f"Handball {self._team_id}"

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return self._attributes
