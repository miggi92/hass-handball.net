import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import (
    DOMAIN,
    CONF_TEAM_ID,
    CONF_TOURNAMENT_ID,
    CONF_ENTITY_TYPE,
    ENTITY_TYPE_TEAM,
    ENTITY_TYPE_TOURNAMENT,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    CONF_UPDATE_INTERVAL_LIVE,
    DEFAULT_UPDATE_INTERVAL_LIVE
)

class HandballNetConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._entity_type = None
        self._update_interval = DEFAULT_UPDATE_INTERVAL
        self._update_interval_live = DEFAULT_UPDATE_INTERVAL_LIVE

    @staticmethod
    def async_get_options_flow(config_entry):
        from .options_flow import HandballNetOptionsFlowHandler
        return HandballNetOptionsFlowHandler(config_entry)

    async def _validate_team_id(self, team_id: str) -> tuple[bool, str | None]:
        """Validate team ID against handball.net API and return team name"""
        session = async_get_clientsession(self.hass)
        url = f"https://www.handball.net/a/sportdata/1/teams/{team_id}"
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    team_data = data.get("data")
                    if team_data:
                        team_name = team_data.get("name", team_id)
                        return True, team_name
                return False, None
        except Exception:
            return False, None

    async def _validate_tournament_id(self, tournament_id: str) -> tuple[bool, str | None]:
        """Validate tournament ID against handball.net API and return tournament name"""
        session = async_get_clientsession(self.hass)
        url = f"https://www.handball.net/a/sportdata/1/tournaments/{tournament_id}/table"
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    tournament_data = data.get("data", {}).get("tournament")
                    if tournament_data:
                        tournament_name = tournament_data.get("name", tournament_id)
                        return True, tournament_name
                return False, None
        except Exception:
            return False, None

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        
        if user_input is not None:
            self._entity_type = user_input[CONF_ENTITY_TYPE]
            self._update_interval = user_input.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
            self._update_interval_live = user_input.get(CONF_UPDATE_INTERVAL_LIVE, DEFAULT_UPDATE_INTERVAL_LIVE)
            
            if self._entity_type == ENTITY_TYPE_TEAM:
                return await self.async_step_team()
            elif self._entity_type == ENTITY_TYPE_TOURNAMENT:
                return await self.async_step_tournament()

        data_schema = vol.Schema({
            vol.Required(CONF_ENTITY_TYPE): vol.In({
                ENTITY_TYPE_TEAM: "Team",
                ENTITY_TYPE_TOURNAMENT: "Tournament"
            }),
            vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): int,
            vol.Optional(CONF_UPDATE_INTERVAL_LIVE, default=DEFAULT_UPDATE_INTERVAL_LIVE): int
        })

        return self.async_show_form(
            step_id="user", 
            data_schema=data_schema, 
            errors=errors
        )

    async def async_step_team(self, user_input=None):
        """Handle team configuration step."""
        errors = {}
        
        if user_input is not None:
            team_id = user_input.get(CONF_TEAM_ID)
            if not team_id:
                errors[CONF_TEAM_ID] = "invalid_team_id"
            else:
                # Check if already configured
                for entry in self._async_current_entries():
                    if (entry.data.get(CONF_TEAM_ID) == team_id and 
                        entry.data.get(CONF_ENTITY_TYPE) == ENTITY_TYPE_TEAM):
                        errors[CONF_TEAM_ID] = "already_configured"
                        break

                if not errors:
                    is_valid, team_name = await self._validate_team_id(team_id)
                    if not is_valid:
                        errors[CONF_TEAM_ID] = "team_not_found"
                    else:
                        # Create the final data dictionary
                        data = {
                            CONF_ENTITY_TYPE: ENTITY_TYPE_TEAM,
                            CONF_TEAM_ID: team_id,
                            "team_name": team_name,
                            CONF_UPDATE_INTERVAL: self._update_interval,
                            CONF_UPDATE_INTERVAL_LIVE: self._update_interval_live
                        }
                        title = f"Team: {team_name}" if team_name else f"Team {team_id}"
                        return self.async_create_entry(title=title, data=data)

        data_schema = vol.Schema({
            vol.Required(CONF_TEAM_ID): str,
        })

        return self.async_show_form(
            step_id="team", 
            data_schema=data_schema, 
            errors=errors
        )

    async def async_step_tournament(self, user_input=None):
        """Handle tournament configuration step."""
        errors = {}
        
        if user_input is not None:
            tournament_id = user_input.get(CONF_TOURNAMENT_ID)
            if not tournament_id:
                errors[CONF_TOURNAMENT_ID] = "invalid_tournament_id"
            else:
                # Check if already configured
                for entry in self._async_current_entries():
                    if (entry.data.get(CONF_TOURNAMENT_ID) == tournament_id and 
                        entry.data.get(CONF_ENTITY_TYPE) == ENTITY_TYPE_TOURNAMENT):
                        errors[CONF_TOURNAMENT_ID] = "already_configured"
                        break

                if not errors:
                    is_valid, tournament_name = await self._validate_tournament_id(tournament_id)
                    if not is_valid:
                        errors[CONF_TOURNAMENT_ID] = "tournament_not_found"
                    else:
                        # Create the final data dictionary
                        data = {
                            CONF_ENTITY_TYPE: ENTITY_TYPE_TOURNAMENT,
                            CONF_TOURNAMENT_ID: tournament_id,
                            "tournament_name": tournament_name,
                            CONF_UPDATE_INTERVAL: self._update_interval,
                            CONF_UPDATE_INTERVAL_LIVE: self._update_interval_live
                        }
                        title = f"Tournament: {tournament_name}" if tournament_name else f"Tournament {tournament_id}"
                        return self.async_create_entry(title=title, data=data)

        data_schema = vol.Schema({
            vol.Required(CONF_TOURNAMENT_ID): str,
        })

        return self.async_show_form(
            step_id="tournament", 
            data_schema=data_schema, 
            errors=errors
        )
