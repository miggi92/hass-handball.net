from homeassistant.core import HomeAssistant

from .const import (
    CONF_ENTITY_TYPE,
    CONF_TEAM_ID,
    CONF_TEAM_MAPPING,
    CONF_TOURNAMENT_ID,
    ENTITY_TYPE_CLUB,
    ENTITY_TYPE_TEAM,
    ENTITY_TYPE_TOURNAMENT,
)
from .coordinator import HandballDataUpdateCoordinator
from .sensors import (
    HandballAllGamesSensor,
    HandballAuswaertsspielSensor,
    HandballHealthSensor,
    HandballHeimspielSensor,
    HandballLiveTickerEventsSensor,
    HandballLiveTickerSensor,
    HandballNextMatchSensor,
    HandballStatisticsSensor,
    HandballTablePositionSensor,
    HandballTournamentTableSensor,
    HandballTournamentTeamPositionSensor,
)


async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    entity_type = entry.data.get(CONF_ENTITY_TYPE, ENTITY_TYPE_TEAM)

    if entity_type == ENTITY_TYPE_TEAM:
        await _setup_team_sensors(hass, entry, async_add_entities)
    elif entity_type == ENTITY_TYPE_CLUB:
        await _setup_club_sensors(hass, entry, async_add_entities)
    elif entity_type == ENTITY_TYPE_TOURNAMENT:
        await _setup_tournament_sensors(hass, entry, async_add_entities)


async def _setup_team_sensors(hass: HomeAssistant, entry, async_add_entities):
    coordinator = HandballDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    team_id = entry.data[CONF_TEAM_ID]
    team_name = entry.data.get("team_name", team_id)
    async_add_entities([
        HandballAllGamesSensor(coordinator, entry, team_id, team_name),
        HandballHeimspielSensor(coordinator, entry, team_id, team_name),
        HandballAuswaertsspielSensor(coordinator, entry, team_id, team_name),
        HandballNextMatchSensor(coordinator, entry, team_id, team_name),
        HandballStatisticsSensor(coordinator, entry, team_id, team_name),
        HandballLiveTickerSensor(coordinator, entry, team_id, team_name),
        HandballLiveTickerEventsSensor(coordinator, entry, team_id, team_name),
        HandballTablePositionSensor(coordinator, entry, team_id, team_name),
        HandballHealthSensor(coordinator, entry, team_id, team_name),
    ])


async def _setup_club_sensors(hass: HomeAssistant, entry, async_add_entities):
    coordinator = HandballDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    sensors = []
    for team_name, team_id in entry.data.get(CONF_TEAM_MAPPING, {}).items():
        sensors.extend([
            HandballAllGamesSensor(coordinator, entry, team_id, team_name),
            HandballHeimspielSensor(coordinator, entry, team_id, team_name),
            HandballAuswaertsspielSensor(coordinator, entry, team_id, team_name),
            HandballNextMatchSensor(coordinator, entry, team_id, team_name),
            HandballStatisticsSensor(coordinator, entry, team_id, team_name),
            HandballLiveTickerSensor(coordinator, entry, team_id, team_name),
            HandballLiveTickerEventsSensor(coordinator, entry, team_id, team_name),
            HandballTablePositionSensor(coordinator, entry, team_id, team_name),
            HandballHealthSensor(coordinator, entry, team_id, team_name),
        ])

    async_add_entities(sensors)


async def _setup_tournament_sensors(hass: HomeAssistant, entry, async_add_entities):
    coordinator = HandballDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    tournament_id = entry.data[CONF_TOURNAMENT_ID]
    tournament_bucket = coordinator.data.get("tournament", {}) if coordinator.data else {}
    table_rows = tournament_bucket.get("table_rows", [])

    sensors = [HandballTournamentTableSensor(coordinator, entry, tournament_id)]
    sensors.extend(
        HandballTournamentTeamPositionSensor(coordinator, entry, tournament_id, team_row)
        for team_row in table_rows
    )

    async_add_entities(sensors)