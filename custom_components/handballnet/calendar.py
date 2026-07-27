from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from datetime import datetime, timedelta, timezone
from .const import DOMAIN, CONF_ENTITY_TYPE, CONF_TEAM_MAPPING, ENTITY_TYPE_TEAM, ENTITY_TYPE_CLUB, ENTITY_TYPE_TOURNAMENT
from .calendars import HandballTeamCalendar, HandballTournamentCalendar
from .coordinator import HandballDataUpdateCoordinator
from .device_helpers import async_ensure_club_device

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = getattr(entry, "runtime_data", None)
    if coordinator is None:
        coordinator = HandballDataUpdateCoordinator(hass, entry)
        await coordinator.async_config_entry_first_refresh()
        entry.runtime_data = coordinator

    entity_type = entry.data.get(CONF_ENTITY_TYPE, ENTITY_TYPE_TEAM)
    
    if entity_type == ENTITY_TYPE_TEAM:
        await _setup_team_calendar(hass, entry, async_add_entities, coordinator)
    elif entity_type == ENTITY_TYPE_CLUB:
        await _setup_club_calendar(hass, entry, async_add_entities, coordinator)
    elif entity_type == ENTITY_TYPE_TOURNAMENT:
        await _setup_tournament_calendar(hass, entry, async_add_entities, coordinator)

async def _setup_team_calendar(hass, entry, async_add_entities, coordinator):
    """Setup calendar for team entities"""
    await async_ensure_club_device(hass, entry)

    team_id = entry.data["team_id"]
    team_name = entry.data.get("team_name", team_id)
    entity = HandballTeamCalendar(hass, entry, team_id, team_name, coordinator)

    team_bucket = hass.data.setdefault(DOMAIN, {}).setdefault(team_id, {})
    team_bucket.setdefault("matches", [])
    team_bucket.setdefault("sensors", []).append(entity)
    
    async_add_entities([entity], update_before_add=True)

async def _setup_club_calendar(hass, entry, async_add_entities, coordinator):
    await async_ensure_club_device(hass, entry)

    club_team_mapping = entry.data.get(CONF_TEAM_MAPPING, {})
    entities = []

    for team_name, team_id in club_team_mapping.items():
        team_bucket = hass.data.setdefault(DOMAIN, {}).setdefault(team_id, {})
        team_bucket.setdefault("matches", [])
        team_bucket.setdefault("table_position", None)
        team_bucket.setdefault("team_name", None)
        team_bucket.setdefault("team_logo_url", None)
        team_bucket.setdefault("sensors", [])

        entity = HandballTeamCalendar(hass, entry, team_id, team_name, coordinator)
        team_bucket.setdefault("sensors", []).append(entity)
        entities.append(entity)

    async_add_entities(entities, update_before_add=True)

async def _setup_tournament_calendar(hass, entry, async_add_entities, coordinator):
    """Setup calendar for tournament entities"""
    tournament_id = entry.data["tournament_id"]
    entity = HandballTournamentCalendar(hass, entry, tournament_id, coordinator)
    
    # Add calendar to sensors list
    tournament_key = f"tournament_{tournament_id}"
    tournament_bucket = hass.data.setdefault(DOMAIN, {}).setdefault(tournament_key, {})
    tournament_bucket.setdefault("sensors", []).append(entity)
    
    async_add_entities([entity], update_before_add=True)