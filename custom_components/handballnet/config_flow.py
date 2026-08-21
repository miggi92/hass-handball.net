import asyncio
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import re
from .const import (
    DOMAIN,
    CONF_CLUB_ID,
    CONF_FEDERATION_ID,
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
    HANDBALL_NET_NEW_API_BASE_URL,
    HANDBALL_NET_WEB_URL,
)

# Gender ids as returned by the new /api/new API
_GENDER_LABELS = {"M": "männlich", "F": "weiblich", "S": "gemischt"}

CONF_TEAM_INPUT_MODE = "team_input_mode"
CONF_CLUB_QUERY = "club_query"
CONF_CLUB_ID = "club_id"
CONF_SELECTED_TEAM_ID = "selected_team_id"

TEAM_INPUT_MODE_MANUAL = "manual"
TEAM_INPUT_MODE_CLUB_SEARCH = "club_search"

CONF_TOURNAMENT_INPUT_MODE = "tournament_input_mode"
CONF_COMPETITION_QUERY = "competition_query"
CONF_SELECTED_COMPETITION_ID = "selected_competition_id"
CONF_SELECTED_PHASE_ID = "selected_phase_id"

TOURNAMENT_INPUT_MODE_CLUB = "club_search"
TOURNAMENT_INPUT_MODE_COMPETITION = "competition_search"


class HandballNetConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._entity_type = None
        self._update_interval = DEFAULT_UPDATE_INTERVAL
        self._update_interval_live = DEFAULT_UPDATE_INTERVAL_LIVE
        self._club_options: dict[str, str] = {}
        self._club_clean_names: dict[str, str] = {}
        self._club_federation_ids: dict[str, str] = {}
        self._team_options: dict[str, str] = {}
        self._team_base_names: dict[str, str] = {}
        self._team_variants: dict[str, str] = {}
        self._selected_club_id: str | None = None
        self._selected_club_name: str | None = None
        self._competition_options: dict[str, str] = {}
        self._competition_names: dict[str, str] = {}
        self._selected_competition_id: str | None = None
        self._selected_competition_name: str | None = None
        self._phase_options: dict[str, str] = {}

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

    def _compose_team_display_name(
        self,
        team_name: str | None,
        club_name: str | None = None,
        team_variant: str | None = None,
    ) -> str:
        """Build a stable display name for a team."""
        normalized_team_name = (team_name or "").strip()
        normalized_club_name = (club_name or "").strip()
        normalized_variant = (team_variant or "").strip()

        if normalized_club_name and normalized_variant:
            return f"{normalized_club_name} {normalized_variant}".strip()

        if normalized_club_name:
            if normalized_team_name.startswith(f"{normalized_club_name} "):
                return normalized_team_name
            if normalized_team_name == normalized_club_name and normalized_variant:
                return f"{normalized_team_name} {normalized_variant}".strip()
            if normalized_team_name:
                return f"{normalized_club_name} {normalized_team_name}".strip()
            return normalized_club_name

        if (
            normalized_variant
            and normalized_team_name
            and not normalized_team_name.endswith(f" {normalized_variant}")
        ):
            return f"{normalized_team_name} {normalized_variant}".strip()

        return normalized_team_name or "Team"

    def _build_team_mapping(self, selected_team_ids: list[str]) -> dict[str, str]:
        team_mapping: dict[str, str] = {}
        used_keys: set[str] = set()
        selected_club_name = (self._selected_club_name or "").strip()

        for team_id in selected_team_ids:
            team_name = self._team_base_names.get(
                team_id, self._team_options.get(team_id, team_id)
            )
            team_variant = self._team_variants.get(team_id)
            stable_team_name = self._compose_team_display_name(
                team_name,
                selected_club_name,
                team_variant,
            )

            stable_key = self._normalize_team_key(stable_team_name, used_keys)
            team_mapping[stable_key] = team_id

        return team_mapping

    def _get_existing_selected_team_ids(self, entry) -> list[str]:
        """Return existing team ids that are still valid for the current club."""
        existing_team_ids = list(entry.data.get(CONF_TEAM_MAPPING, {}).values())
        return [team_id for team_id in existing_team_ids if team_id in self._team_options]

    def _get_reconfigure_entry(self):
        """Return the config entry currently being reconfigured."""
        context = getattr(self, "context", {}) or {}
        entry_id = context.get("entry_id")
        if not entry_id:
            return None

        if not getattr(self, "hass", None):
            return None

        return self.hass.config_entries.async_get_entry(entry_id)

    async def _api_get_new(
        self, path: str, params: dict, referer: str
    ) -> dict | None:
        """Get JSON data from a new (/api/new) handball.net API path."""
        session = async_get_clientsession(self.hass)
        url = f"{HANDBALL_NET_NEW_API_BASE_URL}/{path}"
        headers = {"Referer": referer}

        try:
            async with session.get(url, params=params, headers=headers) as resp:
                if resp.status != 200:
                    return None
                payload = await resp.json()
        except Exception:
            return None

        if not payload or not payload.get("success"):
            return None

        return payload

    async def _api_get_new_paginated(
        self, path: str, params: dict, referer: str
    ) -> list:
        """Get all pages of a paginated new-API list endpoint."""
        results: list = []
        page = 1
        last_page = 1

        while page <= last_page:
            payload = await self._api_get_new(
                path, {**params, "page": page}, referer
            )
            if not payload:
                break

            results.extend(payload.get("data", []) or [])

            pagination = payload.get("pagination") or {}
            last_page = pagination.get("last_page", last_page) or last_page
            page += 1

        return results

    @staticmethod
    def _format_age_category(age_category_name: str | None) -> str | None:
        """Format an age category name like 'B-JUGEND' into 'B-Jugend'."""
        if not age_category_name:
            return None
        return "-".join(part.capitalize() for part in age_category_name.split("-"))

    @staticmethod
    def _format_gender(gender_id: str | None, gender_name: str | None) -> str | None:
        """Format a gender id/name into a German display label."""
        if gender_id and gender_id in _GENDER_LABELS:
            return _GENDER_LABELS[gender_id]
        return gender_name

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

        title = self._compose_team_display_name(team_name, club_name, team_variant)

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

        federation_id = self._club_federation_ids.get(club_id)
        if federation_id:
            data[CONF_FEDERATION_ID] = federation_id

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
        payload = await self._api_get_new(
            "teams/clubs",
            {"all": "1", "filter[search]": query},
            referer=HANDBALL_NET_WEB_URL,
        )
        clubs = payload.get("data", []) if payload else []

        club_options: dict[str, str] = {}
        self._club_clean_names = {}
        self._club_federation_ids = {}
        for club in clubs:
            club_id = club.get("id")
            club_name = club.get("name")
            if club_id is None or not club_name:
                continue

            club_id = str(club_id)
            self._club_clean_names[club_id] = club_name

            federation = club.get("federation") or {}
            federation_id = federation.get("id")
            if federation_id is not None:
                self._club_federation_ids[club_id] = str(federation_id)

            federation_name = federation.get("name")
            club_options[club_id] = (
                f"{club_name} ({federation_name})" if federation_name else club_name
            )

        return club_options

    async def _get_team_phase(self, team_id: str) -> dict | None:
        """Best-effort lookup of a team's current phase (league/season group)."""
        payload = await self._api_get_new(
            "matches",
            {"team_id": team_id, "page": 1},
            referer=f"{HANDBALL_NET_WEB_URL}team/{team_id}",
        )
        matches = payload.get("data", []) if payload else []
        if not matches:
            return None

        phase = matches[0].get("phase") or {}
        phase_id = phase.get("id")
        if phase_id is None:
            return None

        competition = phase.get("competition") or {}
        return {
            "id": str(phase_id),
            "name": phase.get("name"),
            "competition_name": competition.get("name"),
        }

    async def _get_team_league_name(self, team_id: str) -> str | None:
        """Best-effort lookup of a team's current league/competition name."""
        phase = await self._get_team_phase(team_id)
        return phase.get("competition_name") if phase else None

    async def _search_competitions(self, query: str) -> dict[str, str]:
        """Search competitions by name and return competition_id -> display_name map."""
        payload = await self._api_get_new(
            "competitions", {"name": query}, referer=HANDBALL_NET_WEB_URL
        )
        competitions = payload.get("data", []) if payload else []

        competition_options: dict[str, str] = {}
        self._competition_names = {}
        for competition in competitions:
            competition_id = competition.get("id")
            name = competition.get("name")
            if competition_id is None or not name:
                continue

            competition_id = str(competition_id)

            championship = competition.get("championship") or {}
            federation = championship.get("federation") or {}
            federation_name = federation.get("name")

            category = competition.get("category") or {}
            gender_info = category.get("gender") or {}
            age_info = category.get("age") or {}
            gender_label = self._format_gender(gender_info.get("id"), gender_info.get("name"))
            age_label = self._format_age_category(age_info.get("name"))

            detail_parts = [part for part in (age_label, gender_label, federation_name) if part]

            self._competition_names[competition_id] = name
            competition_options[competition_id] = (
                f"{name} ({', '.join(detail_parts)})" if detail_parts else name
            )

        return competition_options

    async def _get_phases_for_competition(self, competition_id: str) -> dict[str, str]:
        """Get the phases (season groups/Staffeln) for a competition."""
        payload = await self._api_get_new(
            "phases", {"competition_id": competition_id}, referer=HANDBALL_NET_WEB_URL
        )
        phases = payload.get("data", []) if payload else []

        phase_options: dict[str, str] = {}
        for phase in phases:
            phase_id = phase.get("id")
            name = phase.get("name")
            if phase_id is None or not name:
                continue

            phase_options[str(phase_id)] = name

        return phase_options

    @staticmethod
    def _compose_tournament_name(
        competition_name: str | None, phase_name: str | None
    ) -> str | None:
        if competition_name and phase_name:
            return f"{competition_name} ({phase_name})"
        return competition_name or phase_name

    def _is_tournament_already_configured(self, tournament_id: str) -> bool:
        return any(
            entry.data.get(CONF_TOURNAMENT_ID) == tournament_id
            and entry.data.get(CONF_ENTITY_TYPE) == ENTITY_TYPE_TOURNAMENT
            for entry in self._async_current_entries()
        )

    def _create_tournament_entry(self, tournament_id: str, tournament_name: str | None):
        """Create config entry for a tournament."""
        data = {
            CONF_ENTITY_TYPE: ENTITY_TYPE_TOURNAMENT,
            CONF_TOURNAMENT_ID: tournament_id,
            "tournament_name": tournament_name,
            CONF_UPDATE_INTERVAL: self._update_interval,
            CONF_UPDATE_INTERVAL_LIVE: self._update_interval_live,
        }
        title = (
            f"Tournament: {tournament_name}" if tournament_name else f"Tournament {tournament_id}"
        )
        return self.async_create_entry(title=title, data=data)

    async def _get_teams_for_club(self, club_id: str) -> dict[str, str]:
        """Get teams for a club and return team_id -> display_name map."""
        params = {"club_id": club_id}
        federation_id = self._club_federation_ids.get(club_id)
        if federation_id:
            params["federation_id"] = federation_id

        teams = await self._api_get_new_paginated(
            "teams", params, referer=f"{HANDBALL_NET_WEB_URL}club/{club_id}"
        )

        team_options: dict[str, str] = {}
        self._team_base_names = {}
        self._team_variants = {}
        for team in teams:
            team_id = team.get("id")
            team_name = team.get("name")
            if team_id is None or not team_name:
                continue

            team_id = str(team_id)
            club_info = team.get("club") or {}
            if not self._selected_club_name:
                self._selected_club_name = club_info.get("name")

            base_team_name, team_number = self._strip_team_suffix(team_name)

            gender = team.get("gender") or {}
            age_category = team.get("age_category") or {}
            gender_label = self._format_gender(gender.get("id"), gender.get("name"))
            age_label = self._format_age_category(age_category.get("name"))

            variant_parts = [
                part for part in (team_number, age_label, gender_label) if part
            ]
            team_variant = " ".join(variant_parts) if variant_parts else None

            self._team_base_names[team_id] = base_team_name or team_name
            if team_variant:
                self._team_variants[team_id] = team_variant

            team_options[team_id] = self._compose_team_display_name(
                base_team_name or team_name,
                self._selected_club_name,
                team_variant,
            )

        if team_options:
            team_ids = list(team_options.keys())
            league_names = await asyncio.gather(
                *(self._get_team_league_name(team_id) for team_id in team_ids),
                return_exceptions=True,
            )
            for team_id, league_name in zip(team_ids, league_names):
                if isinstance(league_name, Exception) or not league_name:
                    continue
                team_options[team_id] = f"{team_options[team_id]} ({league_name})"

        return team_options

    @staticmethod
    def async_get_options_flow(config_entry):
        from .options_flow import HandballNetOptionsFlowHandler

        return HandballNetOptionsFlowHandler(config_entry)

    async def _validate_team_id(self, team_id: str) -> tuple[bool, str | None]:
        """Validate team ID against handball.net API and return team name"""
        payload = await self._api_get_new(
            f"teams/{team_id}", {}, referer=f"{HANDBALL_NET_WEB_URL}team/{team_id}"
        )
        team_data = payload.get("data") if payload else None
        if team_data:
            team_name = team_data.get("name", team_id)
            return True, team_name

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

        title = self._compose_team_display_name(team_name, club_name, team_variant)

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
        old_club_id = entry.data.get(CONF_CLUB_ID)
        data_updates = {
            CONF_ENTITY_TYPE: ENTITY_TYPE_CLUB,
            CONF_CLUB_ID: club_id,
            "club_name": club_name,
            CONF_TEAM_MAPPING: team_mapping,
        }

        federation_id = self._club_federation_ids.get(club_id)
        if federation_id:
            data_updates[CONF_FEDERATION_ID] = federation_id

        title = club_name or club_id

        self.hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, **data_updates},
            title=title,
        )

        for old_team_id in old_team_ids:
            self.hass.data.get(DOMAIN, {}).pop(old_team_id, None)

        if old_club_id and old_club_id != club_id:
            from .device_helpers import async_remove_stale_club_device

            await async_remove_stale_club_device(self.hass, entry, old_club_id)

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
            input_mode = user_input.get(CONF_TOURNAMENT_INPUT_MODE, TOURNAMENT_INPUT_MODE_CLUB)

            if input_mode == TOURNAMENT_INPUT_MODE_CLUB:
                club_query = user_input.get(CONF_CLUB_QUERY, "").strip()
                if len(club_query) < 2:
                    errors[CONF_CLUB_QUERY] = "invalid_club_query"
                else:
                    self._club_options = await self._search_clubs(club_query)
                    if not self._club_options:
                        errors[CONF_CLUB_QUERY] = "club_not_found"
                    else:
                        return await self.async_step_tournament_select_club()

            elif input_mode == TOURNAMENT_INPUT_MODE_COMPETITION:
                competition_query = user_input.get(CONF_COMPETITION_QUERY, "").strip()
                if len(competition_query) < 2:
                    errors[CONF_COMPETITION_QUERY] = "invalid_competition_query"
                else:
                    self._competition_options = await self._search_competitions(
                        competition_query
                    )
                    if not self._competition_options:
                        errors[CONF_COMPETITION_QUERY] = "competition_not_found"
                    else:
                        return await self.async_step_tournament_select_competition()

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_TOURNAMENT_INPUT_MODE, default=TOURNAMENT_INPUT_MODE_CLUB
                ): vol.In(
                    {
                        TOURNAMENT_INPUT_MODE_CLUB: "Search by Club",
                        TOURNAMENT_INPUT_MODE_COMPETITION: "Search by Competition",
                    }
                ),
                vol.Optional(CONF_CLUB_QUERY): str,
                vol.Optional(CONF_COMPETITION_QUERY): str,
            }
        )

        return self.async_show_form(
            step_id="tournament", data_schema=data_schema, errors=errors
        )

    async def async_step_tournament_select_club(self, user_input=None):
        """Handle club selection for tournament setup (search-by-club path)."""
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
                    return await self.async_step_tournament_select_team()

        if not self._club_options:
            return await self.async_step_tournament()

        data_schema = vol.Schema(
            {
                vol.Required(CONF_CLUB_ID): vol.In(self._club_options),
            }
        )

        return self.async_show_form(
            step_id="tournament_select_club",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_tournament_select_team(self, user_input=None):
        """Resolve a tournament from a team's current phase (search-by-club path)."""
        errors = {}

        if user_input is not None:
            team_id = user_input.get(CONF_SELECTED_TEAM_ID)
            if not team_id or team_id not in self._team_options:
                errors[CONF_SELECTED_TEAM_ID] = "invalid_team_selection"
            else:
                phase = await self._get_team_phase(team_id)
                if not phase:
                    errors[CONF_SELECTED_TEAM_ID] = "tournament_not_found"
                elif self._is_tournament_already_configured(phase["id"]):
                    errors[CONF_SELECTED_TEAM_ID] = "already_configured"
                else:
                    tournament_name = self._compose_tournament_name(
                        phase.get("competition_name"), phase.get("name")
                    )
                    return self._create_tournament_entry(phase["id"], tournament_name)

        if not self._team_options:
            return await self.async_step_tournament()

        data_schema = vol.Schema(
            {
                vol.Required(CONF_SELECTED_TEAM_ID): vol.In(self._team_options),
            }
        )

        return self.async_show_form(
            step_id="tournament_select_team",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_tournament_select_competition(self, user_input=None):
        """Handle competition selection (search-by-competition path)."""
        errors = {}

        if user_input is not None:
            competition_id = user_input.get(CONF_SELECTED_COMPETITION_ID)
            if not competition_id or competition_id not in self._competition_options:
                errors[CONF_SELECTED_COMPETITION_ID] = "invalid_competition_selection"
            else:
                self._selected_competition_id = competition_id
                self._selected_competition_name = self._competition_names.get(
                    competition_id, self._competition_options.get(competition_id)
                )
                self._phase_options = await self._get_phases_for_competition(competition_id)
                if not self._phase_options:
                    errors[CONF_SELECTED_COMPETITION_ID] = "no_phases_found"
                else:
                    return await self.async_step_tournament_select_phase()

        if not self._competition_options:
            return await self.async_step_tournament()

        data_schema = vol.Schema(
            {
                vol.Required(CONF_SELECTED_COMPETITION_ID): vol.In(self._competition_options),
            }
        )

        return self.async_show_form(
            step_id="tournament_select_competition",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_tournament_select_phase(self, user_input=None):
        """Handle phase/Staffel selection (search-by-competition path)."""
        errors = {}

        if user_input is not None:
            phase_id = user_input.get(CONF_SELECTED_PHASE_ID)
            if not phase_id or phase_id not in self._phase_options:
                errors[CONF_SELECTED_PHASE_ID] = "invalid_phase_selection"
            elif self._is_tournament_already_configured(phase_id):
                errors[CONF_SELECTED_PHASE_ID] = "already_configured"
            else:
                tournament_name = self._compose_tournament_name(
                    self._selected_competition_name, self._phase_options.get(phase_id)
                )
                return self._create_tournament_entry(phase_id, tournament_name)

        if not self._phase_options:
            return await self.async_step_tournament()

        data_schema = vol.Schema(
            {
                vol.Required(CONF_SELECTED_PHASE_ID): vol.In(self._phase_options),
            }
        )

        return self.async_show_form(
            step_id="tournament_select_phase",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input=None):
        """Handle reconfiguration of existing entries."""
        errors = {}
        entry = self._get_reconfigure_entry()

        if entry is None:
            return self.async_abort(reason="invalid_reconfigure_entry")

        entity_type = entry.data.get(CONF_ENTITY_TYPE, ENTITY_TYPE_TEAM)
        if entity_type not in (ENTITY_TYPE_TEAM, ENTITY_TYPE_CLUB):
            return self.async_abort(reason="invalid_reconfigure_entry")

        current_team_id = entry.data.get(CONF_TEAM_ID, "")
        self._club_options = {}
        self._club_clean_names = {}
        self._club_federation_ids = {}
        self._team_options = {}
        self._team_base_names = {}
        self._team_variants = {}

        if entity_type == ENTITY_TYPE_CLUB and user_input is None:
            existing_club_id = entry.data.get(CONF_CLUB_ID)
            if existing_club_id:
                self._selected_club_id = existing_club_id
                self._selected_club_name = entry.data.get("club_name")
                existing_federation_id = entry.data.get(CONF_FEDERATION_ID)
                if existing_federation_id:
                    self._club_federation_ids[existing_club_id] = existing_federation_id
                self._team_options = await self._get_teams_for_club(existing_club_id)
                if self._team_options:
                    return await self.async_step_reconfigure_select_team()

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
                        return await self.async_step_reconfigure_select_club()

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

    async def async_step_reconfigure_select_club(self, user_input=None):
        """Handle club selection during reconfiguration."""
        errors = {}
        entry = self._get_reconfigure_entry()

        if entry is None:
            return self.async_abort(reason="invalid_reconfigure_entry")

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
                    return await self.async_step_reconfigure_select_team()

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

    async def async_step_reconfigure_select_team(self, user_input=None):
        """Handle final team selection during reconfiguration."""
        errors = {}
        entry = self._get_reconfigure_entry()

        if entry is None:
            return self.async_abort(reason="invalid_reconfigure_entry")

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

        existing_team_ids = self._get_existing_selected_team_ids(entry)
        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_SELECTED_TEAM_ID,
                    default=existing_team_ids,
                ): cv.multi_select(self._team_options),
            }
        )

        return self.async_show_form(
            step_id="reconfigure_select_team",
            data_schema=data_schema,
            errors=errors,
        )
