import os
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from .const import DOMAIN, CONF_TEAM_ID, CONF_TEAM_MAPPING, CONF_TOURNAMENT_ID, CONF_ENTITY_TYPE, ENTITY_TYPE_TEAM, ENTITY_TYPE_CLUB, ENTITY_TYPE_TOURNAMENT

PLATFORMS = ["sensor", "calendar", "binary_sensor"]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

async def async_reload_config(hass: HomeAssistant):
    for entry in hass.config_entries.async_entries(DOMAIN):
        await hass.config_entries.async_reload(entry.entry_id)

async def async_refresh_team_data(hass: HomeAssistant, call):
    """Service to refresh team data"""
    team_id = call.data.get("team_id")
    for entry in hass.config_entries.async_entries(DOMAIN):
        coordinator = getattr(entry, "runtime_data", None)
        if coordinator is None:
            continue

        team_buckets = (coordinator.data or {}).get("teams", {})
        if team_id in team_buckets:
            await coordinator.async_request_refresh()
            return

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

_LOVELACE_CARDS = [
    "handball-tournament-table-card.js",
    "handball-team-card.js",
]


async def async_setup(hass: HomeAssistant, config: dict):
    # Register Lovelace card JS files as static resources
    from homeassistant.components.frontend import add_extra_js_url
    try:
        from homeassistant.components.http import StaticPathConfig
    except ImportError:
        StaticPathConfig = None

    www_dir = os.path.join(os.path.dirname(__file__), "www")
    static_files = []
    for filename in _LOVELACE_CARDS:
        url_path = f"/{DOMAIN}/{filename}"
        file_path = os.path.join(www_dir, filename)
        if os.path.isfile(file_path):
            static_files.append((url_path, file_path))
            add_extra_js_url(hass, url_path)

    if static_files:
        if hasattr(hass.http, "async_register_static_paths") and StaticPathConfig is not None:
            await hass.http.async_register_static_paths(
                [
                    StaticPathConfig(url_path, file_path, cache_headers=False)
                    for url_path, file_path in static_files
                ]
            )
        else:
            for url_path, file_path in static_files:
                hass.http.register_static_path(url_path, file_path, cache_headers=False)

    hass.services.async_register(DOMAIN, "reload_config", async_reload_config)
    hass.services.async_register(DOMAIN, "refresh_team_data", async_refresh_team_data)
    hass.services.async_register(DOMAIN, "diagnose_team", async_diagnose_team)
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    from .coordinator import HandballDataUpdateCoordinator

    hass.data.setdefault(DOMAIN, {})
    
    entity_type = entry.data.get(CONF_ENTITY_TYPE, ENTITY_TYPE_TEAM)
    
    if entity_type == ENTITY_TYPE_TEAM:
        team_id = entry.data[CONF_TEAM_ID]
        hass.data[DOMAIN][team_id] = {
            "matches": [],
            "table_position": None,
            "team_name": None,
            "team_logo_url": None,
            "sensors": []
        }
    elif entity_type == ENTITY_TYPE_CLUB:
        club_id = entry.data.get("club_id", entry.entry_id)
        team_mapping = entry.data.get(CONF_TEAM_MAPPING, {})
        hass.data[DOMAIN][club_id] = {
            "club_name": entry.data.get("club_name"),
            "team_mapping": team_mapping,
            "sensors": []
        }

        from .device_helpers import async_prune_stale_team_devices
        await async_prune_stale_team_devices(hass, entry, set(team_mapping.keys()))
    elif entity_type == ENTITY_TYPE_TOURNAMENT:
        tournament_id = entry.data[CONF_TOURNAMENT_ID]
        tournament_key = f"tournament_{tournament_id}"
        hass.data[DOMAIN][tournament_key] = {
            "tournament_info": {},
            "table_rows": [],
            "matches": [],
            "sensors": []
        }

    coordinator = HandballDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        entity_type = entry.data.get(CONF_ENTITY_TYPE, ENTITY_TYPE_TEAM)
        if entity_type == ENTITY_TYPE_TEAM:
            team_id = entry.data[CONF_TEAM_ID]
            hass.data[DOMAIN].pop(team_id, None)
        elif entity_type == ENTITY_TYPE_CLUB:
            club_id = entry.data.get("club_id", entry.entry_id)
            team_mapping = entry.data.get(CONF_TEAM_MAPPING, {})
            for team_id in team_mapping.values():
                hass.data[DOMAIN].pop(team_id, None)
            hass.data[DOMAIN].pop(club_id, None)
        elif entity_type == ENTITY_TYPE_TOURNAMENT:
            tournament_id = entry.data[CONF_TOURNAMENT_ID]
            tournament_key = f"tournament_{tournament_id}"
            hass.data[DOMAIN].pop(tournament_key, None)

        entry.runtime_data = None
    
    if not hass.config_entries.async_entries(DOMAIN):
        hass.services.async_remove(DOMAIN, "reload_config")
        hass.services.async_remove(DOMAIN, "refresh_team_data")
        hass.services.async_remove(DOMAIN, "diagnose_team")
    return unload_ok
