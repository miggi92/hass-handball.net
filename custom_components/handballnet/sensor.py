from homeassistant.helpers.entity import Entity
import requests

def setup_platform(hass, config, add_entities, discovery_info=None):
    team_id = config.get("team_id")
    add_entities([HandballNetSensor(team_id)], True)

class HandballNetSensor(Entity):
    def __init__(self, team_id):
        self._team_id = team_id
        self._state = None
        self._attributes = {}

    def update(self):
        response = requests.get(f"https://api.handball.net/teams/{self._team_id}/matches")
        data = response.json()
        self._state = f"{data['teamName']} ({len(data['matches'])} Spiele)"
        self._attributes = {
            "spiele": data['matches']
        }

    @property
    def name(self):
        return f"Handball Team {self._team_id}"

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return self._attributes
