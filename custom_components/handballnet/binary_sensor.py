from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from datetime import datetime, timezone
from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    team_id = entry.data["team_id"]
    entity = HandballLiveBinarySensor(hass, entry, team_id)
    
    # Add binary sensor to sensors list for logo updates
    if "sensors" not in hass.data[DOMAIN][team_id]:
        hass.data[DOMAIN][team_id]["sensors"] = []
    hass.data[DOMAIN][team_id]["sensors"].append(entity)
    
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
            "model": "Handball Team",
            "entry_type": "service"
        }
        self._attr_icon = "mdi:handball"

    def update_entity_picture(self, logo_url: str) -> None:
        """Update entity picture with team logo"""
        if logo_url and logo_url.strip():
            self._attr_entity_picture = logo_url

    def update_device_name(self, team_name: str) -> None:
        """Update device name with actual team name"""
        if team_name and team_name != "":
            self._attr_device_info["name"] = f"Handball {team_name}"

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
