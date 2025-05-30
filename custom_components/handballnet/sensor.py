from homeassistant.helpers.event import async_call_later
from homeassistant.core import HomeAssistant
from datetime import datetime, timezone
import logging

from .const import (
    DOMAIN,
    CONF_TEAM_ID,
    CONF_TOURNAMENT_ID,
    CONF_ENTITY_TYPE,
    ENTITY_TYPE_TEAM,
    ENTITY_TYPE_TOURNAMENT,
    CONF_UPDATE_INTERVAL,
    CONF_UPDATE_INTERVAL_LIVE,
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL_LIVE
)
from .api import HandballNetAPI
from .sensors import (
    HandballAllGamesSensor,
    HandballHeimspielSensor,
    HandballAuswaertsspielSensor,
    HandballNextMatchSensor,
    HandballStatisticsSensor,
    HandballLiveTickerSensor,
    HandballLiveTickerEventsSensor,
    HandballTablePositionSensor,
    HandballHealthSensor
)
from .sensors.tournament_table_sensor import HandballTournamentTableSensor
from .sensors.tournament_team_position_sensor import HandballTournamentTeamPositionSensor

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    entity_type = entry.data.get(CONF_ENTITY_TYPE, ENTITY_TYPE_TEAM)
    
    if entity_type == ENTITY_TYPE_TEAM:
        await _setup_team_sensors(hass, entry, async_add_entities)
    elif entity_type == ENTITY_TYPE_TOURNAMENT:
        await _setup_tournament_sensors(hass, entry, async_add_entities)

async def _setup_team_sensors(hass: HomeAssistant, entry, async_add_entities):
    """Setup sensors for team entities"""
    team_id = entry.data[CONF_TEAM_ID]
    update_interval = entry.options.get(CONF_UPDATE_INTERVAL, entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))
    live_interval = entry.options.get(CONF_UPDATE_INTERVAL_LIVE, entry.data.get(CONF_UPDATE_INTERVAL_LIVE, DEFAULT_UPDATE_INTERVAL_LIVE))

    api = HandballNetAPI(hass)
    
    # Create team sensor instances
    all_sensor = HandballAllGamesSensor(hass, entry, team_id, api)
    heim_sensor = HandballHeimspielSensor(hass, entry, team_id)
    aus_sensor = HandballAuswaertsspielSensor(hass, entry, team_id)
    next_match_sensor = HandballNextMatchSensor(hass, entry, team_id, api)
    statistics_sensor = HandballStatisticsSensor(hass, entry, team_id)
    live_sensor = HandballLiveTickerSensor(hass, entry, team_id)
    live_events_sensor = HandballLiveTickerEventsSensor(hass, entry, team_id, api)
    table_sensor = HandballTablePositionSensor(hass, entry, team_id, api)
    health_sensor = HandballHealthSensor(hass, entry, team_id, api)

    # Store sensor references
    hass.data[DOMAIN][team_id]["sensors"] = [all_sensor, heim_sensor, aus_sensor, next_match_sensor, statistics_sensor, live_sensor, live_events_sensor, table_sensor, health_sensor]

    async_add_entities([all_sensor, heim_sensor, aus_sensor, next_match_sensor, statistics_sensor, live_sensor, live_events_sensor, table_sensor, health_sensor])

    async def update_all(now=None):
        try:
            await all_sensor.async_update()
            # Update device names for all sensors after getting team info
            team_name = hass.data.get(DOMAIN, {}).get(team_id, {}).get("team_name")
            team_logo_url = hass.data.get(DOMAIN, {}).get(team_id, {}).get("team_logo_url")
            
            if team_name:
                for sensor in hass.data[DOMAIN][team_id]["sensors"]:
                    if hasattr(sensor, 'update_device_name'):
                        sensor.update_device_name(team_name)
                        
                # Logo nur für den all_sensor (Alle Spiele)
                if team_logo_url and hasattr(all_sensor, 'update_entity_picture'):
                    all_sensor.update_entity_picture(team_logo_url)
        except Exception as e:
            _LOGGER.error("Error updating all games sensor: %s", e)

        try:
            await next_match_sensor.async_update()
        except Exception as e:
            _LOGGER.error("Error updating next match sensor: %s", e)

        try:
            await statistics_sensor.async_update()
        except Exception as e:
            _LOGGER.error("Error updating statistics sensor: %s", e)
            
        try:
            await table_sensor.async_update()
        except Exception as e:
            _LOGGER.error("Error updating table position sensor: %s", e)
            
        try:
            await health_sensor.async_update()
        except Exception as e:
            _LOGGER.error("Error updating health sensor: %s", e)
            
        all_sensor.async_write_ha_state()
        heim_sensor.async_write_ha_state()
        aus_sensor.async_write_ha_state()
        next_match_sensor.async_write_ha_state()
        statistics_sensor.async_write_ha_state()
        live_sensor.update_state()
        live_sensor.async_write_ha_state()
        table_sensor.async_write_ha_state()
        health_sensor.async_write_ha_state()
        await schedule_next_poll()

    async def schedule_next_poll():
        now_ts = datetime.now(timezone.utc).timestamp()
        matches = hass.data.get(DOMAIN, {}).get(team_id, {}).get("matches", [])
        is_live = any(
            match.get("startsAt", 0) / 1000 <= now_ts <= match.get("startsAt", 0) / 1000 + 7200
            for match in matches
        )
        interval = live_interval if is_live else update_interval
        async_call_later(hass, interval, update_all)

    await update_all()

async def _setup_tournament_sensors(hass: HomeAssistant, entry, async_add_entities):
    """Setup sensors for tournament entities"""
    tournament_id = entry.data[CONF_TOURNAMENT_ID]
    api = HandballNetAPI(hass)
    
    # Create main tournament table sensor
    tournament_table_sensor = HandballTournamentTableSensor(hass, entry, tournament_id, api)
    
    # Store sensor references
    tournament_key = f"tournament_{tournament_id}"
    if tournament_key not in hass.data[DOMAIN]:
        hass.data[DOMAIN][tournament_key] = {"sensors": []}
    hass.data[DOMAIN][tournament_key]["sensors"].append(tournament_table_sensor)

    # Start with just the main table sensor
    entities_to_add = [tournament_table_sensor]

    async def update_tournament(now=None):
        try:
            # Update main table sensor first
            await tournament_table_sensor.async_update()
            tournament_table_sensor.async_write_ha_state()
            
            # Get updated table data
            table_rows = hass.data.get(DOMAIN, {}).get(tournament_key, {}).get("table_rows", [])
            
            # Create team position sensors if they don't exist
            if table_rows:
                await _create_team_position_sensors_if_needed(hass, entry, tournament_id, table_rows, async_add_entities)
            
        except Exception as e:
            _LOGGER.error("Error updating tournament table sensor: %s", e)
        
        # Schedule next update
        update_interval = entry.options.get(CONF_UPDATE_INTERVAL, entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))
        async_call_later(hass, update_interval, update_tournament)

    async_add_entities(entities_to_add)
    await update_tournament()

async def _create_team_position_sensors_if_needed(hass: HomeAssistant, entry, tournament_id: str, table_rows: list, async_add_entities):
    """Create team position sensors if they don't exist yet"""
    tournament_key = f"tournament_{tournament_id}"
    existing_sensors = hass.data.get(DOMAIN, {}).get(tournament_key, {}).get("sensors", [])
    
    # Check if we already have team position sensors
    from .sensors.tournament_team_position_sensor import HandballTournamentTeamPositionSensor
    existing_position_sensors = [s for s in existing_sensors if isinstance(s, HandballTournamentTeamPositionSensor)]
    
    # If we already have position sensors, don't create new ones
    if existing_position_sensors:
        return
    
    # Create sensors for each team position
    new_sensors = []
    for team_data in table_rows:
        team_position_sensor = HandballTournamentTeamPositionSensor(hass, entry, tournament_id, team_data)
        team_position_sensor.update_team_data(team_data)  # Set initial data
        new_sensors.append(team_position_sensor)
        
        # Add to stored sensors list
        hass.data[DOMAIN][tournament_key]["sensors"].append(team_position_sensor)
    
    # Add new sensors to Home Assistant
    if new_sensors:
        async_add_entities(new_sensors)
        _LOGGER.info("Created %d team position sensors for tournament %s", len(new_sensors), tournament_id)