from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from datetime import datetime, timezone
from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    team_id = entry.data["team_id"]
    entity = HandballLiveBinarySensor(hass, entry, team_id)
    async_add_entities([entity], update_before_add=True)

class HandballLiveBinarySensor(BinarySensorEntity):
    def __init__(self, hass, entry, team_id):
        self.hass = hass
        self._team_id = team_id
        self._attr_name = f"Handball Live {team_id}"
        self._attr_unique_id = f"handball_live_{team_id}"
        self._attr_config_entry_id = entry.entry_id
        self._attr_device_info = {
            "identifiers": {(DOMAIN, team_id)},
            "name": f"Handball Team {team_id}",
            "manufacturer": "handball.net",
            "model": "Team Kalender + Sensor",
            "entry_type": "service"
        }
        self._attr_icon = "mdi:handball"

    @property
    def is_on(self) -> bool:
        now_ts = datetime.now(timezone.utc).timestamp()
        matches = self.hass.data.get(DOMAIN, {}).get(self._team_id, {}).get("matches", [])
        return any(
            match.get("startsAt", 0) / 1000 <= now_ts <= match.get("startsAt", 0) / 1000 + 7200
            for match in matches
        )

    @property
    def extra_state_attributes(self):
        return {
            "team_id": self._team_id,
            "matches_count": len(self.hass.data.get(DOMAIN, {}).get(self._team_id, {}).get("matches", []))
        }
