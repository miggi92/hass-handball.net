from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from .const import DOMAIN

PLATFORMS = ["sensor", "calendar", "binary_sensor"]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

async def async_reload_config(hass: HomeAssistant):
    for entry in hass.config_entries.async_entries(DOMAIN):
        await hass.config_entries.async_reload(entry.entry_id)

async def async_refresh_team_data(hass: HomeAssistant, call):
    """Service to refresh team data"""
    team_id = call.data.get("team_id")
    if team_id in hass.data[DOMAIN]:
        # Trigger update for all sensors of this team
        sensors = hass.data[DOMAIN][team_id].get("sensors", [])
        for sensor in sensors:
            if hasattr(sensor, 'async_update'):
                await sensor.async_update()
                sensor.async_write_ha_state()

async def async_diagnose_team(hass: HomeAssistant, call):
    """Service to diagnose team configuration"""
    import logging
    team_id = call.data.get("team_id")
    _LOGGER = logging.getLogger(__name__)
    
    from .api import HandballNetAPI
    api = HandballNetAPI(hass)
    
    _LOGGER.info("=== HANDBALL.NET DIAGNOSE FOR TEAM %s ===", team_id)
    
    # Test team info
    team_info = await api.get_team_info(team_id)
    _LOGGER.info("Team Info: %s", team_info)
    
    # Test schedule
    schedule = await api.get_team_schedule(team_id)
    _LOGGER.info("Schedule: %d matches found", len(schedule) if schedule else 0)
    
    # Test logo
    if schedule:
        logo_url = api.extract_team_logo_url(schedule, team_id)
        _LOGGER.info("Logo URL: %s", logo_url)
    
    _LOGGER.info("=== END DIAGNOSE ===")

async def async_setup(hass: HomeAssistant, config: dict):
    hass.services.async_register(DOMAIN, "reload_config", async_reload_config)
    hass.services.async_register(DOMAIN, "refresh_team_data", async_refresh_team_data)
    hass.services.async_register(DOMAIN, "diagnose_team", async_diagnose_team)
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.data["team_id"]] = {
        "matches": [],
        "table_position": None,
        "team_name": None,
        "team_logo_url": None,
        "sensors": []
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.data["team_id"])
    if not hass.config_entries.async_entries(DOMAIN):
        hass.services.async_remove(DOMAIN, "reload_config")
        hass.services.async_remove(DOMAIN, "refresh_team_data")
        hass.services.async_remove(DOMAIN, "diagnose_team")
    return unload_ok
