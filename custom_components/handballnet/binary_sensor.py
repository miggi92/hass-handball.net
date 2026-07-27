from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from datetime import datetime, timezone
from .const import (
    DOMAIN,
    CONF_ENTITY_TYPE,
    CONF_TEAM_MAPPING,
    ENTITY_TYPE_TEAM,
    ENTITY_TYPE_CLUB,
)
from .coordinator import HandballDataUpdateCoordinator
from .sensors.team.base_sensor import HandballBaseSensor


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    entity_type = entry.data.get(CONF_ENTITY_TYPE, ENTITY_TYPE_TEAM)
    if entity_type not in (ENTITY_TYPE_TEAM, ENTITY_TYPE_CLUB):
        return

    coordinator = getattr(entry, "runtime_data", None)
    if coordinator is None:
        coordinator = HandballDataUpdateCoordinator(hass, entry)
        await coordinator.async_config_entry_first_refresh()
        entry.runtime_data = coordinator

    entities = []

    if entity_type == ENTITY_TYPE_TEAM:
        team_id = entry.data["team_id"]
        team_name = entry.data.get("team_name", team_id)
        entity = HandballTeamLiveBinarySensor(coordinator, entry, team_id, team_name)
        team_bucket = hass.data.setdefault(DOMAIN, {}).setdefault(team_id, {})
        team_bucket.setdefault("sensors", []).append(entity)
        entities.append(entity)
    else:
        for team_name, team_id in entry.data.get(CONF_TEAM_MAPPING, {}).items():
            team_bucket = hass.data.setdefault(DOMAIN, {}).setdefault(team_id, {})
            team_bucket.setdefault("matches", [])
            team_bucket.setdefault("table_position", None)
            team_bucket.setdefault("team_name", None)
            team_bucket.setdefault("team_logo_url", None)
            entity = HandballTeamLiveBinarySensor(coordinator, entry, team_id, team_name)
            team_bucket.setdefault("sensors", []).append(entity)
            entities.append(entity)

    async_add_entities(entities, update_before_add=True)


class HandballTeamLiveBinarySensor(HandballBaseSensor, BinarySensorEntity):
    def __init__(self, coordinator, entry, team_id, team_name):
        super().__init__(coordinator, entry, team_id, team_name)

        display_name = self._resolve_display_name(team_name)
        self._attr_name = f"{display_name} Live"
        self._attr_unique_id = self._build_unique_id("live")
        self._attr_icon = "mdi:handball"

    @property
    def is_on(self) -> bool:
        now_ts = datetime.now(timezone.utc).timestamp()
        matches = self._get_team_bucket().get("matches", [])
        return any(
            match.get("startsAt", 0) / 1000
            <= now_ts
            <= match.get("startsAt", 0) / 1000 + 7200
            for match in matches
        )

    @property
    def extra_state_attributes(self):
        matches = self._get_team_bucket().get("matches", [])
        return {
            "team_id": self._team_id,
            "matches_count": len(matches),
        }
