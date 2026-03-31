import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from urllib.parse import quote_plus
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

CONF_TEAM_INPUT_MODE = "team_input_mode"
CONF_CLUB_QUERY = "club_query"
CONF_CLUB_ID = "club_id"
CONF_SELECTED_TEAM_ID = "selected_team_id"

TEAM_INPUT_MODE_MANUAL = "manual"
TEAM_INPUT_MODE_CLUB_SEARCH = "club_search"

class HandballNetConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._entity_type = None
        self._update_interval = DEFAULT_UPDATE_INTERVAL
        self._update_interval_live = DEFAULT_UPDATE_INTERVAL_LIVE
        self._club_options: dict[str, str] = {}
        self._team_options: dict[str, str] = {}

    async def _api_get(self, path: str):
        """Get JSON data from handball.net API path."""
        session = async_get_clientsession(self.hass)
        url = f"https://www.handball.net/a/sportdata/1/{path}"

        try:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return None
                return await resp.json()
        except Exception:
            return None

    def _is_team_already_configured(self, team_id: str) -> bool:
        """Check if the team is already configured."""
        for entry in self._async_current_entries():
            if (
                entry.data.get(CONF_TEAM_ID) == team_id
                and entry.data.get(CONF_ENTITY_TYPE) == ENTITY_TYPE_TEAM
            ):
                return True
        return False

    def _create_team_entry(self, team_id: str, team_name: str | None):
        """Create config entry for a team."""
        data = {
            CONF_ENTITY_TYPE: ENTITY_TYPE_TEAM,
            CONF_TEAM_ID: team_id,
            "team_name": team_name,
            CONF_UPDATE_INTERVAL: self._update_interval,
            CONF_UPDATE_INTERVAL_LIVE: self._update_interval_live,
        }
        title = f"Team: {team_name}" if team_name else f"Team {team_id}"
        return self.async_create_entry(title=title, data=data)

    async def _search_clubs(self, query: str) -> dict[str, str]:
        """Search clubs by query and return club_id -> display_name map."""
        encoded_query = quote_plus(query)
        data = await self._api_get(f"clubs/search?query={encoded_query}")
        clubs = data.get("data", []) if data else []

        club_options: dict[str, str] = {}
        for club in clubs:
            club_id = club.get("id")
            club_name = club.get("name")
            if club_id and club_name:
                acronym = club.get("acronym")
                if acronym:
                    club_options[club_id] = f"{club_name} ({acronym})"
                else:
                    club_options[club_id] = club_name

        return club_options

    async def _get_teams_for_club(self, club_id: str) -> dict[str, str]:
        """Get teams for a club and return team_id -> display_name map."""
        data = await self._api_get(f"clubs/{club_id}/teams")
        teams = data.get("data", []) if data else []

        team_options: dict[str, str] = {}
        for team in teams:
            team_id = team.get("id")
            team_name = team.get("name")
            if team_id and team_name:
                acronym = team.get("acronym")
                if acronym:
                    team_options[team_id] = f"{team_name} ({acronym})"
                else:
                    team_options[team_id] = team_name

        return team_options

    @staticmethod
    def async_get_options_flow(config_entry):
        from .options_flow import HandballNetOptionsFlowHandler
        return HandballNetOptionsFlowHandler(config_entry)

    async def _validate_team_id(self, team_id: str) -> tuple[bool, str | None]:
        """Validate team ID against handball.net API and return team name"""
        data = await self._api_get(f"teams/{team_id}")
        if not data:
            return False, None

        team_data = data.get("data")
        if team_data:
            team_name = team_data.get("name", team_id)
            return True, team_name

        return False, None

    async def _validate_tournament_id(self, tournament_id: str) -> tuple[bool, str | None]:
        """Validate tournament ID against handball.net API and return tournament name"""
        data = await self._api_get(f"tournaments/{tournament_id}/table")
        if not data:
            return False, None

        tournament_data = data.get("data", {}).get("tournament")
        if tournament_data:
            tournament_name = tournament_data.get("name", tournament_id)
            return True, tournament_name

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
            input_mode = user_input.get(CONF_TEAM_INPUT_MODE, TEAM_INPUT_MODE_MANUAL)

            if input_mode == TEAM_INPUT_MODE_MANUAL:
                team_id = user_input.get(CONF_TEAM_ID, "").strip()
                if not team_id:
                    errors[CONF_TEAM_ID] = "invalid_team_id"
                elif self._is_team_already_configured(team_id):
                    errors[CONF_TEAM_ID] = "already_configured"
                else:
                    is_valid, team_name = await self._validate_team_id(team_id)
                    if not is_valid:
                        errors[CONF_TEAM_ID] = "team_not_found"
                    else:
                        return self._create_team_entry(team_id, team_name)

            elif input_mode == TEAM_INPUT_MODE_CLUB_SEARCH:
                club_query = user_input.get(CONF_CLUB_QUERY, "").strip()
                if len(club_query) < 2:
                    errors[CONF_CLUB_QUERY] = "invalid_club_query"
                else:
                    self._club_options = await self._search_clubs(club_query)
                    if not self._club_options:
                        errors[CONF_CLUB_QUERY] = "club_not_found"
                    else:
                        return await self.async_step_team_select_club()

        data_schema = vol.Schema({
            vol.Required(CONF_TEAM_INPUT_MODE, default=TEAM_INPUT_MODE_MANUAL): vol.In({
                TEAM_INPUT_MODE_MANUAL: "Manual Team ID",
                TEAM_INPUT_MODE_CLUB_SEARCH: "Search by Club"
            }),
            vol.Optional(CONF_TEAM_ID): str,
            vol.Optional(CONF_CLUB_QUERY): str,
        })

        return self.async_show_form(
            step_id="team", 
            data_schema=data_schema, 
            errors=errors
        )

    async def async_step_team_select_club(self, user_input=None):
        """Handle club selection after searching clubs."""
        errors = {}

        if user_input is not None:
            club_id = user_input.get(CONF_CLUB_ID)
            if not club_id or club_id not in self._club_options:
                errors[CONF_CLUB_ID] = "invalid_club_selection"
            else:
                self._team_options = await self._get_teams_for_club(club_id)
                if not self._team_options:
                    errors[CONF_CLUB_ID] = "no_teams_found"
                else:
                    return await self.async_step_team_select_team()

        if not self._club_options:
            return await self.async_step_team()

        data_schema = vol.Schema({
            vol.Required(CONF_CLUB_ID): vol.In(self._club_options),
        })

        return self.async_show_form(
            step_id="team_select_club",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_team_select_team(self, user_input=None):
        """Handle final team selection after club selection."""
        errors = {}

        if user_input is not None:
            team_id = user_input.get(CONF_SELECTED_TEAM_ID)
            if not team_id or team_id not in self._team_options:
                errors[CONF_SELECTED_TEAM_ID] = "invalid_team_selection"
            elif self._is_team_already_configured(team_id):
                errors[CONF_SELECTED_TEAM_ID] = "already_configured"
            else:
                team_name = self._team_options.get(team_id)
                return self._create_team_entry(team_id, team_name)

        if not self._team_options:
            return await self.async_step_team()

        data_schema = vol.Schema({
            vol.Required(CONF_SELECTED_TEAM_ID): vol.In(self._team_options),
        })

        return self.async_show_form(
            step_id="team_select_team",
            data_schema=data_schema,
            errors=errors,
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
