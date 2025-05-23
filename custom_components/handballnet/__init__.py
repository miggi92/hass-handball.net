from .const import DOMAIN

async def async_setup(hass, config):
    return True

async def async_setup_entry(hass, entry):
    team_id = entry.data["team_id"]

    # Gemeinsame Datenstruktur anlegen
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][team_id] = {"matches": []}

    # Entry wurde eingerichtet, Plattformen (sensor, calendar) werden per forward_setup geladen
    await hass.config_entries.async_forward_entry_setups(entry, ["sensor", "calendar"])

    return True
