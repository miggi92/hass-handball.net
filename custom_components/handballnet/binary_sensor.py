from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from datetime import datetime, timezone
from .const import DOMAIN, CONF_ENTITY_TYPE, ENTITY_TYPE_TEAM
from .sensors.base_sensor import HandballBaseSensor

async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    # Only create binary sensor for teams, not tournaments
    entity_type = entry.data.get(CONF_ENTITY_TYPE, ENTITY_TYPE_TEAM)
    if entity_type != ENTITY_TYPE_TEAM:
        return
        
    team_id = entry.data["team_id"]
    entity = HandballTeamLiveBinarySensor(hass, entry, team_id)
    
    # Add binary sensor to sensors list for logo updates
    if "sensors" not in hass.data[DOMAIN][team_id]:
        hass.data[DOMAIN][team_id]["sensors"] = []
    hass.data[DOMAIN][team_id]["sensors"].append(entity)
    
    async_add_entities([entity], update_before_add=True)

class HandballTeamLiveBinarySensor(HandballBaseSensor, BinarySensorEntity):
    def __init__(self, hass, entry, team_id):
        super().__init__(hass, entry, team_id)
        
        # Use team name from config if available, fallback to team_id
        team_name = entry.data.get("team_name", team_id)
        self._attr_name = f"{team_name} Live"
        self._attr_unique_id = f"handball_team_{team_id}_live"
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
