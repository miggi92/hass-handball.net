import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from urllib.parse import quote_plus
import re
from .const import (
    DOMAIN,
    CONF_CLUB_ID,
    CONF_TEAM_ID,
    CONF_TEAM_MAPPING,
    CONF_TOURNAMENT_ID,
    CONF_ENTITY_TYPE,
    ENTITY_TYPE_TEAM,
    ENTITY_TYPE_CLUB,
    ENTITY_TYPE_TOURNAMENT,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    CONF_UPDATE_INTERVAL_LIVE,
    DEFAULT_UPDATE_INTERVAL_LIVE,
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
        self._club_clean_names: dict[str, str] = {}
        self._team_options: dict[str, str] = {}
        self._team_base_names: dict[str, str] = {}
        self._team_variants: dict[str, str] = {}
        self._selected_club_id: str | None = None
        self._selected_club_name: str | None = None

    @staticmethod
    def _split_trailing_parentheses(value: str | None) -> tuple[str | None, str | None]:
        """Split 'Name (SUFFIX)' into ('Name', 'SUFFIX')."""
        if not value:
            return value, None

        stripped_value = value.strip()
        if stripped_value.endswith(")") and " (" in stripped_value:
            base, suffix = stripped_value.rsplit(" (", 1)
            return base.strip(), suffix[:-1].strip()

        return stripped_value, None

    @staticmethod
    def _extract_team_variant(
        acronym: str | None, fallback_suffix: str | None = None
    ) -> str | None:
        """Extract the trailing team variant, e.g. 2 from TSV Willsbach 2."""
        source = (fallback_suffix or "").strip()
        if not source:
            return None

        match = re.search(r"(\d+)$", source)
        if match:
            return match.group(1)

        return None

    @staticmethod
    def _extract_league_prefix(acronym: str | None) -> str | None:
        """Extract the league prefix, e.g. M from M-BK."""
        if not acronym:
            return None

        prefix = acronym.strip().split("-", 1)[0].strip()
        return prefix or None

    @staticmethod
    def _strip_team_suffix(team_name: str | None) -> tuple[str | None, str | None]:
        """Split a team name into base name and trailing numeric suffix."""
        if not team_name:
            return team_name, None

        stripped_name = team_name.strip()
        parts = stripped_name.rsplit(" ", 1)
        if len(parts) == 2 and parts[1].isdigit():
            return parts[0].strip(), parts[1]

        return stripped_name, None

    def _resolve_team_variant(
        self, team_name: str | None, acronym: str | None = None
    ) -> str | None:
        """Build the compact team variant used in device names."""
        base_name, team_number = self._strip_team_suffix(team_name)
        league_prefix = self._extract_league_prefix(acronym)

        if league_prefix and team_number:
            return f"{league_prefix}{team_number}"

        return league_prefix or team_number

    @staticmethod
    def _normalize_team_key(team_name: str, used_keys: set[str]) -> str:
        key = re.sub(r"\s+", " ", team_name.strip())
        if not key:
            key = "Team"

        candidate = key
        counter = 2
        while candidate in used_keys:
            candidate = f"{key} {counter}"
            counter += 1

        used_keys.add(candidate)
        return candidate

    def _build_team_mapping(self, selected_team_ids: list[str]) -> dict[str, str]:
        team_mapping: dict[str, str] = {}
        used_keys: set[str] = set()
        selected_club_name = (self._selected_club_name or "").strip()

        for team_id in selected_team_ids:
            team_name = self._team_base_names.get(
                team_id, self._team_options.get(team_id, team_id)
            )
            team_variant = self._team_variants.get(team_id)
            if selected_club_name and team_variant:
                stable_team_name = f"{selected_club_name} {team_variant}"
            else:
                stable_team_name = team_name
                if team_variant and team_variant not in stable_team_name:
                    stable_team_name = f"{stable_team_name} {team_variant}"

            stable_key = self._normalize_team_key(stable_team_name, used_keys)
            team_mapping[stable_key] = team_id

        return team_mapping

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

    def _is_team_already_configured(
        self,
        team_id: str,
        exclude_entry_id: str | None = None,
    ) -> bool:
        """Check if the team is already configured."""
        for entry in self._async_current_entries():
            if exclude_entry_id and entry.entry_id == exclude_entry_id:
                continue
            entity_type = entry.data.get(CONF_ENTITY_TYPE)
            if (
                entity_type == ENTITY_TYPE_TEAM
                and entry.data.get(CONF_TEAM_ID) == team_id
            ):
                return True
            if (
                entity_type == ENTITY_TYPE_CLUB
                and team_id in entry.data.get(CONF_TEAM_MAPPING, {}).values()
            ):
                return True
        return False

    def _are_team_ids_already_configured(
        self,
        team_ids: list[str],
        exclude_entry_id: str | None = None,
    ) -> bool:
        return any(
            self._is_team_already_configured(team_id, exclude_entry_id)
            for team_id in team_ids
        )

    def _create_team_entry(
        self,
        team_id: str,
        team_name: str | None,
        club_id: str | None = None,
        club_name: str | None = None,
        team_variant: str | None = None,
    ):
        """Create config entry for a team."""
        data = {
            CONF_ENTITY_TYPE: ENTITY_TYPE_TEAM,
            CONF_TEAM_ID: team_id,
            "team_name": team_name,
            CONF_UPDATE_INTERVAL: self._update_interval,
            CONF_UPDATE_INTERVAL_LIVE: self._update_interval_live,
        }

        if club_id:
            data[CONF_CLUB_ID] = club_id
        if club_name:
            data["club_name"] = club_name
        if team_variant:
            data["team_variant"] = team_variant

        title = club_name or team_name or team_id

        return self.async_create_entry(title=title, data=data)

    def _create_club_entry(
        self,
        club_id: str,
        club_name: str | None,
        team_mapping: dict[str, str],
    ):
        data = {
            CONF_ENTITY_TYPE: ENTITY_TYPE_CLUB,
            CONF_CLUB_ID: club_id,
            "club_name": club_name,
            CONF_TEAM_MAPPING: team_mapping,
            CONF_UPDATE_INTERVAL: self._update_interval,
            CONF_UPDATE_INTERVAL_LIVE: self._update_interval_live,
        }

        title = club_name or club_id
        return self.async_create_entry(title=title, data=data)

    def _normalize_team_selection(
        self, team_name: str | None, acronym: str | None = None
    ) -> tuple[str | None, str | None]:
        """Normalize a selected team name and derive its compact variant."""
        base_team_name, team_number = self._strip_team_suffix(team_name)
        team_variant = self._resolve_team_variant(team_name, acronym)
        return base_team_name or team_name, team_variant

    async def _search_clubs(self, query: str) -> dict[str, str]:
        """Search clubs by query and return club_id -> display_name map."""
        encoded_query = quote_plus(query)
        data = await self._api_get(f"clubs/search?query={encoded_query}")
        clubs = data.get("data", []) if data else []

        club_options: dict[str, str] = {}
        self._club_clean_names = {}
        for club in clubs:
            club_id = club.get("id")
            club_name = club.get("name")
            if club_id and club_name:
                clean_club_name, _ = self._split_trailing_parentheses(club_name)
                self._club_clean_names[club_id] = clean_club_name or club_name

                acronym = club.get("acronym")
                if acronym:
                    club_options[club_id] = (
                        f"{clean_club_name or club_name} ({acronym})"
                    )
                else:
                    club_options[club_id] = clean_club_name or club_name

        return club_options

    async def _get_teams_for_club(self, club_id: str) -> dict[str, str]:
        """Get teams for a club and return team_id -> display_name map."""
        data = await self._api_get(f"clubs/{club_id}/teams")
        teams = data.get("data", []) if data else []

        team_options: dict[str, str] = {}
        self._team_base_names = {}
        self._team_variants = {}
        for team in teams:
            team_id = team.get("id")
            team_name = team.get("name")
            if team_id and team_name:
                default_tournament = team.get("defaultTournament")
                acronym = (
                    default_tournament.get("acronym") if default_tournament else None
                )
                base_team_name, team_variant = self._normalize_team_selection(
                    team_name, acronym
                )
                self._team_base_names[team_id] = base_team_name or team_name
                if team_variant:
                    self._team_variants[team_id] = team_variant

                if acronym:
                    team_options[team_id] = f"{base_team_name or team_name} ({acronym})"
                else:
                    team_options[team_id] = base_team_name or team_name

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

    async def _validate_tournament_id(
        self, tournament_id: str
    ) -> tuple[bool, str | None]:
        """Validate tournament ID against handball.net API and return tournament name"""
        data = await self._api_get(f"tournaments/{tournament_id}/table")
        if not data:
            return False, None

        tournament_data = data.get("data", {}).get("tournament")
        if tournament_data:
            tournament_name = tournament_data.get("name", tournament_id)
            return True, tournament_name

        return False, None

    async def _update_team_entry(
        self,
        entry,
        team_id: str,
        team_name: str | None,
        club_id: str | None = None,
        club_name: str | None = None,
        team_variant: str | None = None,
    ):
        """Update an existing team config entry and reload it."""
        current_team_id = entry.data.get(CONF_TEAM_ID, "")
        data_updates = {
            CONF_TEAM_ID: team_id,
            "team_name": team_name,
            "team_variant": team_variant,
        }

        if club_id:
            data_updates[CONF_CLUB_ID] = club_id
        if club_name:
            data_updates["club_name"] = club_name

        title = club_name or team_name or team_id

        self.hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, **data_updates},
            title=title,
        )
        await self.hass.config_entries.async_reload(entry.entry_id)
        self.hass.data.get(DOMAIN, {}).pop(current_team_id, None)
        return self.async_abort(reason="reconfigure_successful")

    async def _update_club_entry(
        self,
        entry,
        club_id: str,
        club_name: str | None,
        team_mapping: dict[str, str],
    ):
        old_team_ids = list(entry.data.get(CONF_TEAM_MAPPING, {}).values())
        data_updates = {
            CONF_ENTITY_TYPE: ENTITY_TYPE_CLUB,
            CONF_CLUB_ID: club_id,
            "club_name": club_name,
            CONF_TEAM_MAPPING: team_mapping,
        }

        title = club_name or club_id

        self.hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, **data_updates},
            title=title,
        )

        for old_team_id in old_team_ids:
            self.hass.data.get(DOMAIN, {}).pop(old_team_id, None)

        await self.hass.config_entries.async_reload(entry.entry_id)
        return self.async_abort(reason="reconfigure_successful")

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            self._entity_type = user_input[CONF_ENTITY_TYPE]
            self._update_interval = user_input.get(
                CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
            )
            self._update_interval_live = user_input.get(
                CONF_UPDATE_INTERVAL_LIVE, DEFAULT_UPDATE_INTERVAL_LIVE
            )

            if self._entity_type == ENTITY_TYPE_TEAM:
                return await self.async_step_team()
            elif self._entity_type == ENTITY_TYPE_TOURNAMENT:
                return await self.async_step_tournament()

        data_schema = vol.Schema(
            {
                vol.Required(CONF_ENTITY_TYPE): vol.In(
                    {ENTITY_TYPE_TEAM: "Team", ENTITY_TYPE_TOURNAMENT: "Tournament"}
                ),
                vol.Optional(
                    CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL
                ): int,
                vol.Optional(
                    CONF_UPDATE_INTERVAL_LIVE, default=DEFAULT_UPDATE_INTERVAL_LIVE
                ): int,
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
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
                        clean_team_name, parsed_suffix = (
                            self._split_trailing_parentheses(team_name)
                        )
                        return self._create_team_entry(
                            team_id,
                            clean_team_name or team_name,
                            team_variant=self._resolve_team_variant(parsed_suffix),
                        )

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

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_TEAM_INPUT_MODE, default=TEAM_INPUT_MODE_MANUAL
                ): vol.In(
                    {
                        TEAM_INPUT_MODE_MANUAL: "Manual Team ID",
                        TEAM_INPUT_MODE_CLUB_SEARCH: "Search by Club",
                    }
                ),
                vol.Optional(CONF_TEAM_ID): str,
                vol.Optional(CONF_CLUB_QUERY): str,
            }
        )

        return self.async_show_form(
            step_id="team", data_schema=data_schema, errors=errors
        )

    async def async_step_team_select_club(self, user_input=None):
        """Handle club selection after searching clubs."""
        errors = {}

        if user_input is not None:
            club_id = user_input.get(CONF_CLUB_ID)
            if not club_id or club_id not in self._club_options:
                errors[CONF_CLUB_ID] = "invalid_club_selection"
            else:
                self._selected_club_id = club_id
                self._selected_club_name = self._club_clean_names.get(
                    club_id, self._club_options.get(club_id)
                )
                self._team_options = await self._get_teams_for_club(club_id)
                if not self._team_options:
                    errors[CONF_CLUB_ID] = "no_teams_found"
                else:
                    return await self.async_step_team_select_team()

        if not self._club_options:
            return await self.async_step_team()

        data_schema = vol.Schema(
            {
                vol.Required(CONF_CLUB_ID): vol.In(self._club_options),
            }
        )

        return self.async_show_form(
            step_id="team_select_club",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_team_select_team(self, user_input=None):
        """Handle final team selection after club selection."""
        errors = {}

        if user_input is not None:
            selected_team_ids = user_input.get(CONF_SELECTED_TEAM_ID, [])
            if isinstance(selected_team_ids, str):
                selected_team_ids = [selected_team_ids]

            if not selected_team_ids:
                errors[CONF_SELECTED_TEAM_ID] = "invalid_team_selection"
            elif any(
                team_id not in self._team_options for team_id in selected_team_ids
            ):
                errors[CONF_SELECTED_TEAM_ID] = "invalid_team_selection"
            elif self._are_team_ids_already_configured(selected_team_ids):
                errors[CONF_SELECTED_TEAM_ID] = "already_configured"
            else:
                team_mapping = self._build_team_mapping(selected_team_ids)
                return self._create_club_entry(
                    self._selected_club_id or self._selected_club_name or "club",
                    self._selected_club_name,
                    team_mapping,
                )

        if not self._team_options:
            return await self.async_step_team()

        data_schema = vol.Schema(
            {
                vol.Required(CONF_SELECTED_TEAM_ID): cv.multi_select(
                    self._team_options
                ),
            }
        )

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
                    if (
                        entry.data.get(CONF_TOURNAMENT_ID) == tournament_id
                        and entry.data.get(CONF_ENTITY_TYPE) == ENTITY_TYPE_TOURNAMENT
                    ):
                        errors[CONF_TOURNAMENT_ID] = "already_configured"
                        break

                if not errors:
                    is_valid, tournament_name = await self._validate_tournament_id(
                        tournament_id
                    )
                    if not is_valid:
                        errors[CONF_TOURNAMENT_ID] = "tournament_not_found"
                    else:
                        # Create the final data dictionary
                        data = {
                            CONF_ENTITY_TYPE: ENTITY_TYPE_TOURNAMENT,
                            CONF_TOURNAMENT_ID: tournament_id,
                            "tournament_name": tournament_name,
                            CONF_UPDATE_INTERVAL: self._update_interval,
                            CONF_UPDATE_INTERVAL_LIVE: self._update_interval_live,
                        }
                        title = (
                            f"Tournament: {tournament_name}"
                            if tournament_name
                            else f"Tournament {tournament_id}"
                        )
                        return self.async_create_entry(title=title, data=data)

        data_schema = vol.Schema(
            {
                vol.Required(CONF_TOURNAMENT_ID): str,
            }
        )

        return self.async_show_form(
            step_id="tournament", data_schema=data_schema, errors=errors
        )

    async def async_step_reconfigure(self, user_input=None):
        """Handle reconfiguration of existing entries."""
        errors = {}
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])

        if entry is None:
            return self.async_abort(reason="invalid_reconfigure_entry")

        entity_type = entry.data.get(CONF_ENTITY_TYPE, ENTITY_TYPE_TEAM)
        if entity_type not in (ENTITY_TYPE_TEAM, ENTITY_TYPE_CLUB):
            return self.async_abort(reason="invalid_reconfigure_entry")

        current_team_id = entry.data.get(CONF_TEAM_ID, "")
        self._club_options = {}
        self._club_clean_names = {}
        self._team_options = {}
        self._team_base_names = {}
        self._team_variants = {}

        if user_input is not None:
            input_mode = user_input.get(CONF_TEAM_INPUT_MODE, TEAM_INPUT_MODE_MANUAL)

            if (
                entity_type == ENTITY_TYPE_CLUB
                or input_mode == TEAM_INPUT_MODE_CLUB_SEARCH
            ):
                club_query = user_input.get(CONF_CLUB_QUERY, "").strip()
                if len(club_query) < 2:
                    errors[CONF_CLUB_QUERY] = "invalid_club_query"
                else:
                    self._club_options = await self._search_clubs(club_query)
                    if not self._club_options:
                        errors[CONF_CLUB_QUERY] = "club_not_found"
                    else:
                        return await self.async_step_reconfigure_select_club(entry)

            elif input_mode == TEAM_INPUT_MODE_MANUAL:
                team_id = user_input.get(CONF_TEAM_ID, "").strip()
                if not team_id:
                    errors[CONF_TEAM_ID] = "invalid_team_id"
                elif self._is_team_already_configured(
                    team_id, exclude_entry_id=entry.entry_id
                ):
                    errors[CONF_TEAM_ID] = "already_configured"
                else:
                    is_valid, team_name = await self._validate_team_id(team_id)
                    if not is_valid:
                        errors[CONF_TEAM_ID] = "team_not_found"
                    else:
                        clean_team_name, team_variant = self._normalize_team_selection(
                            team_name
                        )
                        team_variant = team_variant or entry.data.get("team_variant")
                        return await self._update_team_entry(
                            entry,
                            team_id,
                            clean_team_name or team_name or team_id,
                            team_variant=team_variant,
                            club_name=entry.data.get("club_name"),
                            club_id=entry.data.get(CONF_CLUB_ID),
                        )

        if entity_type == ENTITY_TYPE_CLUB:
            data_schema = vol.Schema(
                {
                    vol.Required(
                        CONF_TEAM_INPUT_MODE, default=TEAM_INPUT_MODE_CLUB_SEARCH
                    ): vol.In(
                        {
                            TEAM_INPUT_MODE_CLUB_SEARCH: "Search by Club",
                        }
                    ),
                    vol.Optional(CONF_CLUB_QUERY): str,
                }
            )
        else:
            data_schema = vol.Schema(
                {
                    vol.Required(
                        CONF_TEAM_INPUT_MODE, default=TEAM_INPUT_MODE_MANUAL
                    ): vol.In(
                        {
                            TEAM_INPUT_MODE_MANUAL: "Manual Team ID",
                            TEAM_INPUT_MODE_CLUB_SEARCH: "Search by Club",
                        }
                    ),
                    vol.Optional(CONF_TEAM_ID): str,
                    vol.Optional(CONF_CLUB_QUERY): str,
                }
            )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_reconfigure_select_club(self, entry, user_input=None):
        """Handle club selection during reconfiguration."""
        errors = {}

        if user_input is not None:
            club_id = user_input.get(CONF_CLUB_ID)
            if not club_id or club_id not in self._club_options:
                errors[CONF_CLUB_ID] = "invalid_club_selection"
            else:
                self._selected_club_id = club_id
                self._selected_club_name = self._club_clean_names.get(
                    club_id, self._club_options.get(club_id)
                )
                self._team_options = await self._get_teams_for_club(club_id)
                if not self._team_options:
                    errors[CONF_CLUB_ID] = "no_teams_found"
                else:
                    return await self.async_step_reconfigure_select_team(entry)

        if not self._club_options:
            return await self.async_step_reconfigure()

        data_schema = vol.Schema(
            {
                vol.Required(CONF_CLUB_ID): vol.In(self._club_options),
            }
        )

        return self.async_show_form(
            step_id="reconfigure_select_club",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_reconfigure_select_team(self, entry, user_input=None):
        """Handle final team selection during reconfiguration."""
        errors = {}

        if user_input is not None:
            selected_team_ids = user_input.get(CONF_SELECTED_TEAM_ID, [])
            if isinstance(selected_team_ids, str):
                selected_team_ids = [selected_team_ids]

            if not selected_team_ids:
                errors[CONF_SELECTED_TEAM_ID] = "invalid_team_selection"
            elif any(
                team_id not in self._team_options for team_id in selected_team_ids
            ):
                errors[CONF_SELECTED_TEAM_ID] = "invalid_team_selection"
            elif self._are_team_ids_already_configured(
                selected_team_ids, exclude_entry_id=entry.entry_id
            ):
                errors[CONF_SELECTED_TEAM_ID] = "already_configured"
            else:
                team_mapping = self._build_team_mapping(selected_team_ids)
                return await self._update_club_entry(
                    entry,
                    self._selected_club_id
                    or entry.data.get(CONF_CLUB_ID)
                    or entry.entry_id,
                    self._selected_club_name or entry.data.get("club_name"),
                    team_mapping,
                )

        if not self._team_options:
            return await self.async_step_reconfigure()

        data_schema = vol.Schema(
            {
                vol.Required(CONF_SELECTED_TEAM_ID): cv.multi_select(
                    self._team_options
                ),
            }
        )

        return self.async_show_form(
            step_id="reconfigure_select_team",
            data_schema=data_schema,
            errors=errors,
        )
