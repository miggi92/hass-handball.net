from typing import Any
from .base_sensor import HandballBaseSensor
from ...const import DOMAIN
from ...api import HandballNetAPI
from ...utils import HandballNetUtils
import logging

_LOGGER = logging.getLogger(__name__)

class HandballAllGamesSensor(HandballBaseSensor):
    def __init__(self, hass, entry, team_id, api: HandballNetAPI):
        super().__init__(hass, entry, team_id)
        self.utils = HandballNetUtils()
        self._api = api
        self._team_id = team_id  # Explicitly set _team_id
        self._state = None
        self._attributes = {}

        # Use team name from config if available, fallback to team_id
        team_name = entry.data.get("team_name", team_id)
        self._attr_name = f"{team_name} Alle Spiele"
        self._attr_unique_id = f"handball_team_{team_id}_all_games"
        self._attr_icon = "mdi:calendar"

    @property
    def state(self) -> str | None:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attributes

    def _extract_essential_match_data(self, matches: list) -> list:
        """Extract only essential match data to reduce memory usage"""
        essential_matches = []

        for match in matches:
            # Get logo URLs and normalize them
            home_logo = match.get("homeTeam", {}).get("logo")
            away_logo = match.get("awayTeam", {}).get("logo")

            essential_match = {
                "id": match.get("id"),
                "startsAt": match.get("startsAt"),
                "state": match.get("state"),
                "homeTeam": {
                    "id": match.get("homeTeam", {}).get("id"),
                    "name": match.get("homeTeam", {}).get("name"),
                    "logo": self.utils.normalize_logo_url(home_logo) if home_logo else None
                },
                "awayTeam": {
                    "id": match.get("awayTeam", {}).get("id"),
                    "name": match.get("awayTeam", {}).get("name"),
                    "logo": self.utils.normalize_logo_url(away_logo) if away_logo else None
                },
                "field": {
                    "name": match.get("field", {}).get("name")
                },
                "homeGoals": match.get("homeGoals"),
                "awayGoals": match.get("awayGoals"),
                "tournament": {
                    "id": match.get("tournament", {}).get("id"),
                    "name": match.get("tournament", {}).get("name")
                },
                # Add computed fields for easier processing
                "isHomeMatch": match.get("homeTeam", {}).get("id") == self._team_id,
                "isAway": match.get("awayTeam", {}).get("id") == self._team_id
            }
            essential_matches.append(essential_match)

        return essential_matches

    async def async_update(self) -> None:
        try:
            matches = await self._api.get_team_schedule(self._team_id)
            if not matches:
                self._state = "Keine Spiele verfügbar"
                self._attributes = {}
                return

            # Extract only essential data
            essential_matches = self._extract_essential_match_data(matches)

            next_match = self.utils.get_next_match_info(essential_matches)
            last_match = self.utils.get_last_match_info(essential_matches)

            self._state = f"Nächstes Spiel: {next_match['opponent']}" if next_match else "Kein nächstes Spiel"
            self._attributes = {
                "next_match": next_match,
                "last_match": last_match,
                "total_matches": len(essential_matches),
                # Only store first 5 upcoming and last 5 played matches in attributes
                "upcoming_matches": [m for m in essential_matches if m.get("startsAt", 0) > 0][:5],
                "recent_matches": [m for m in essential_matches if m.get("state") == "Post"][-5:]
            }

            # Store essential matches in hass.data for other sensors
            if DOMAIN not in self.hass.data:
                self.hass.data[DOMAIN] = {}
            if self._team_id not in self.hass.data[DOMAIN]:
                self.hass.data[DOMAIN][self._team_id] = {}
            self.hass.data[DOMAIN][self._team_id]["matches"] = essential_matches

            # Try to get and store team info for other sensors
            try:
                team_info = await self._api.get_team_info(self._team_id)
                if team_info:
                    self.hass.data[DOMAIN][self._team_id]["team_name"] = team_info.get("name")
                    logo_url = self._api.extract_team_logo_url(matches, self._team_id)
                    if logo_url:
                        self.hass.data[DOMAIN][self._team_id]["team_logo_url"] = logo_url
            except Exception as e:
                _LOGGER.debug("Could not update team info: %s", e)

        except Exception as e:
            _LOGGER.error("Error updating all games sensor for %s: %s", self._team_id, e)
            self._state = "Fehler beim Laden"
            self._attributes = {"error": str(e)}