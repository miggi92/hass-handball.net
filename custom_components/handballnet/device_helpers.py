from homeassistant.helpers import device_registry as dr, entity_registry as er

from .const import CONF_CLUB_ID, CONF_ENTITY_TYPE, DOMAIN, ENTITY_TYPE_CLUB, ENTITY_TYPE_TEAM


async def async_prune_stale_team_devices(hass, entry, keep_team_names: set[str]) -> None:
    """Remove devices/entities for teams no longer present in a club's team mapping.

    Team devices are identified as f"{entry.entry_id}_{team_name}"; reloading a
    config entry only (re-)creates entities for the teams currently listed in
    CONF_TEAM_MAPPING, so unchecked teams would otherwise linger as orphaned
    devices/entities in the registries.
    """
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    prefix = f"{entry.entry_id}_"

    for device in list(dr.async_entries_for_config_entry(device_registry, entry.entry_id)):
        for domain, identifier in device.identifiers:
            if domain != DOMAIN or not identifier.startswith(prefix):
                continue

            team_name = identifier[len(prefix):]
            if team_name in keep_team_names:
                break

            for entity_entry in er.async_entries_for_device(
                entity_registry, device.id, include_disabled_entities=True
            ):
                entity_registry.async_remove(entity_entry.entity_id)

            device_registry.async_remove_device(device.id)
            break


async def async_remove_stale_club_device(hass, entry, old_club_id: str | None) -> None:
    """Remove the previous club device when a club entry is repointed to a different club."""
    new_club_id = entry.data.get(CONF_CLUB_ID, entry.entry_id)
    if not old_club_id or old_club_id == new_club_id:
        return

    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    device = device_registry.async_get_device(identifiers={(DOMAIN, old_club_id)})
    if not device:
        return

    for entity_entry in er.async_entries_for_device(
        entity_registry, device.id, include_disabled_entities=True
    ):
        entity_registry.async_remove(entity_entry.entity_id)

    device_registry.async_remove_device(device.id)


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
