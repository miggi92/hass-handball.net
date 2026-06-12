from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from datetime import datetime, timedelta, timezone
from .const import DOMAIN, CONF_ENTITY_TYPE, CONF_TEAM_MAPPING, ENTITY_TYPE_TEAM, ENTITY_TYPE_CLUB, ENTITY_TYPE_TOURNAMENT
from .calendars import HandballTeamCalendar, HandballTournamentCalendar
from .api import HandballNetAPI

async def async_setup_entry(hass, entry, async_add_entities):
    entity_type = entry.data.get(CONF_ENTITY_TYPE, ENTITY_TYPE_TEAM)
    
    if entity_type == ENTITY_TYPE_TEAM:
        await _setup_team_calendar(hass, entry, async_add_entities)
    elif entity_type == ENTITY_TYPE_CLUB:
        await _setup_club_calendar(hass, entry, async_add_entities)
    elif entity_type == ENTITY_TYPE_TOURNAMENT:
        await _setup_tournament_calendar(hass, entry, async_add_entities)

async def _setup_team_calendar(hass, entry, async_add_entities):
    """Setup calendar for team entities"""
    team_id = entry.data["team_id"]
    team_name = entry.data.get("team_name", team_id)
    entity = HandballTeamCalendar(hass, entry, team_id, team_name)
    
    if "sensors" not in hass.data[DOMAIN][team_id]:
        hass.data[DOMAIN][team_id]["sensors"] = []
    hass.data[DOMAIN][team_id]["sensors"].append(entity)
    
    async_add_entities([entity], update_before_add=True)

async def _setup_club_calendar(hass, entry, async_add_entities):
    club_team_mapping = entry.data.get(CONF_TEAM_MAPPING, {})
    entities = []

    for team_name, team_id in club_team_mapping.items():
        if team_id not in hass.data[DOMAIN]:
            hass.data[DOMAIN][team_id] = {"matches": [], "table_position": None, "team_name": None, "team_logo_url": None, "sensors": []}

        entity = HandballTeamCalendar(hass, entry, team_id, team_name)
        hass.data[DOMAIN][team_id].setdefault("sensors", []).append(entity)
        entities.append(entity)

    async_add_entities(entities, update_before_add=True)

async def _setup_tournament_calendar(hass, entry, async_add_entities):
    """Setup calendar for tournament entities"""
    tournament_id = entry.data["tournament_id"]
    api = HandballNetAPI(hass)
    entity = HandballTournamentCalendar(hass, entry, tournament_id, api)
    
    # Add calendar to sensors list
    tournament_key = f"tournament_{tournament_id}"
    if tournament_key not in hass.data[DOMAIN]:
        hass.data[DOMAIN][tournament_key] = {"sensors": []}
    if "sensors" not in hass.data[DOMAIN][tournament_key]:
        hass.data[DOMAIN][tournament_key]["sensors"] = []
    hass.data[DOMAIN][tournament_key]["sensors"].append(entity)
    
    async_add_entities([entity], update_before_add=True)