from .const import DOMAIN

async def async_setup_entry(hass, entry):
    hass.data.setdefault(DOMAIN, {})
    # Setup Logik
    return True

async def async_unload_entry(hass, entry):
    return True
