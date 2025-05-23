from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_devices):
    team_id = entry.data["team_id"]

    # Gemeinsame Datenstruktur für diesen team_id anlegen
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][team_id] = {"matches": []}

    from .sensor import HandballNetSensor
    from .calendar import HandballCalendar

    sensor = HandballNetSensor(hass, team_id)
    calendar = HandballCalendar(hass, team_id)

    async_add_devices([sensor])
    async_add_devices([calendar])