from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import DOMAIN

PLATFORMS = ["sensor", "calendar", "binary_sensor"]

async def async_reload_config(hass: HomeAssistant):
    for entry in hass.config_entries.async_entries(DOMAIN):
        await hass.config_entries.async_reload(entry.entry_id)

async def async_setup(hass: HomeAssistant, config: dict):
    hass.services.async_register(DOMAIN, "reload_config", async_reload_config)
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.data["team_id"]] = {"matches": []}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.data["team_id"])
    if not hass.config_entries.async_entries(DOMAIN):
        hass.services.async_remove(DOMAIN, "reload_config")
    return unload_ok
