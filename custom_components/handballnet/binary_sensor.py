from homeassistant.components.binary_sensor import BinarySensorEntity
from datetime import datetime, timezone
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    team_id = entry.data["team_id"]
    entity = HandballLiveTickerBinarySensor(hass, entry, team_id)
    async_add_entities([entity], update_before_add=False)

class HandballLiveTickerBinarySensor(BinarySensorEntity):
    def __init__(self, hass, entry, team_id):
        self.hass = hass
        self._team_id = team_id
        self._attr_name = f"Liveticker Aktiv (Binary) {team_id}"
        self._attr_unique_id = f"{team_id}_liveticker_binary"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, team_id)},
            "name": f"Handball Team {team_id}",
            "manufacturer": "handball.net",
            "model": "Team Kalender + Sensor"
        }
        self._attr_icon = "mdi:clock-alert"
        self._attr_should_poll = False
        self._attr_is_on = False

    async def async_update(self):
        now_ts = datetime.now(timezone.utc).timestamp()
        matches = self.hass.data.get(DOMAIN, {}).get(self._team_id, {}).get("matches", [])
        self._attr_is_on = any(
            match.get("startsAt", 0) / 1000 <= now_ts <= match.get("startsAt", 0) / 1000 + 7200
            for match in matches
        )

    @property
    def is_on(self) -> bool:
        return self._attr_is_on

    @property
    def extra_state_attributes(self):
        return {
            "team_id": self._team_id,
            "tracked_matches": len(self.hass.data.get(DOMAIN, {}).get(self._team_id, {}).get("matches", []))
        }
