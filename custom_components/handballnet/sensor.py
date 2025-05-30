from homeassistant.helpers.event import async_call_later
from homeassistant.core import HomeAssistant
from datetime import datetime, timezone
import logging

from .const import (
    DOMAIN,
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
    HandballLiveTickerSensor,
    HandballLiveTickerEventsSensor,
    HandballTablePositionSensor,
    HandballHealthSensor
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    team_id = entry.data["team_id"]
    update_interval = entry.options.get(CONF_UPDATE_INTERVAL, entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))
    live_interval = entry.options.get(CONF_UPDATE_INTERVAL_LIVE, entry.data.get(CONF_UPDATE_INTERVAL_LIVE, DEFAULT_UPDATE_INTERVAL_LIVE))

    api = HandballNetAPI(hass)
    
    # Create sensor instances
    all_sensor = HandballAllGamesSensor(hass, entry, team_id, api)
    heim_sensor = HandballHeimspielSensor(hass, entry, team_id)
    aus_sensor = HandballAuswaertsspielSensor(hass, entry, team_id)
    next_match_sensor = HandballNextMatchSensor(hass, entry, team_id, api)
    live_sensor = HandballLiveTickerSensor(hass, entry, team_id)
    live_events_sensor = HandballLiveTickerEventsSensor(hass, entry, team_id, api)
    table_sensor = HandballTablePositionSensor(hass, entry, team_id, api)
    health_sensor = HandballHealthSensor(hass, entry, team_id, api)

    # Store sensor references for device name updates
    hass.data[DOMAIN][team_id]["sensors"] = [all_sensor, heim_sensor, aus_sensor, next_match_sensor, live_sensor, live_events_sensor, table_sensor, health_sensor]

    async_add_entities([all_sensor, heim_sensor, aus_sensor, next_match_sensor, live_sensor, live_events_sensor, table_sensor, health_sensor])

    async def update_all(now=None):
        try:
            await all_sensor.async_update()
            # Update device names and logos for all sensors after getting team info
            team_name = hass.data.get(DOMAIN, {}).get(team_id, {}).get("team_name")
            team_logo_url = hass.data.get(DOMAIN, {}).get(team_id, {}).get("team_logo_url")
            
            if team_name:
                for sensor in hass.data[DOMAIN][team_id]["sensors"]:
                    sensor.update_device_name(team_name)
                    # Logo nur für den all_sensor (Alle Spiele), nicht für andere
                    if sensor == all_sensor and team_logo_url:
                        sensor.update_entity_picture(team_logo_url)
        except Exception as e:
            _LOGGER.error("Error updating all games sensor: %s", e)

        try:
            await next_match_sensor.async_update()
        except Exception as e:
            _LOGGER.error("Error updating next match sensor: %s", e)
            
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