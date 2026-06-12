from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from datetime import datetime, timezone
from .const import DOMAIN, CONF_ENTITY_TYPE, CONF_TEAM_MAPPING, ENTITY_TYPE_TEAM, ENTITY_TYPE_CLUB
from .sensors.team.base_sensor import HandballBaseSensor

async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    entity_type = entry.data.get(CONF_ENTITY_TYPE, ENTITY_TYPE_TEAM)
    if entity_type not in (ENTITY_TYPE_TEAM, ENTITY_TYPE_CLUB):
        return

    entities = []

    if entity_type == ENTITY_TYPE_TEAM:
        team_id = entry.data["team_id"]
        team_name = entry.data.get("team_name", team_id)
        entity = HandballTeamLiveBinarySensor(hass, entry, team_id, team_name)
        if "sensors" not in hass.data[DOMAIN][team_id]:
            hass.data[DOMAIN][team_id]["sensors"] = []
        hass.data[DOMAIN][team_id]["sensors"].append(entity)
        entities.append(entity)
    else:
        for team_name, team_id in entry.data.get(CONF_TEAM_MAPPING, {}).items():
            if team_id not in hass.data[DOMAIN]:
                hass.data[DOMAIN][team_id] = {"matches": [], "table_position": None, "team_name": None, "team_logo_url": None, "sensors": []}
            entity = HandballTeamLiveBinarySensor(hass, entry, team_id, team_name)
            hass.data[DOMAIN][team_id].setdefault("sensors", []).append(entity)
            entities.append(entity)

    async_add_entities(entities, update_before_add=True)

class HandballTeamLiveBinarySensor(HandballBaseSensor, BinarySensorEntity):
    def __init__(self, hass, entry, team_id, team_name):
        super().__init__(hass, entry, team_id, team_name)

        display_name = self._resolve_display_name(team_name)
        self._attr_name = f"{display_name} Live"
        self._attr_unique_id = self._build_unique_id("live")
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
