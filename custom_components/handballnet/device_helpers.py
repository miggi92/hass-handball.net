from homeassistant.helpers import device_registry as dr

from .const import CONF_CLUB_ID, CONF_ENTITY_TYPE, DOMAIN, ENTITY_TYPE_CLUB, ENTITY_TYPE_TEAM


async def async_ensure_club_device(hass, entry) -> None:
    """Ensure the parent club device exists before entities reference it via via_device."""
    entity_type = entry.data.get(CONF_ENTITY_TYPE, ENTITY_TYPE_TEAM)
    if entity_type not in (ENTITY_TYPE_TEAM, ENTITY_TYPE_CLUB):
        return

    club_id = entry.data.get(CONF_CLUB_ID, entry.entry_id)
    if not club_id:
        return

    club_name = (entry.data.get("club_name") or club_id).strip()
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, club_id)},
        manufacturer="handball.net",
        model="Handball Club",
        name=club_name,
        entry_type=dr.DeviceEntryType.SERVICE,
    )
