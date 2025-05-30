from datetime import datetime, timezone
from typing import Any, Optional
from .base_sensor import HandballBaseSensor
from ..const import DOMAIN
from ..api import HandballNetAPI
from ..utils import get_next_match_info, normalize_logo_url
import logging

_LOGGER = logging.getLogger(__name__)

class HandballNextMatchSensor(HandballBaseSensor):
    def __init__(self, hass, entry, team_id, api: HandballNetAPI):
        super().__init__(hass, entry, team_id)
        self._api = api
        self._state = None
        self._attributes = {}
        
        # Use team name from config if available, fallback to team_id
        team_name = entry.data.get("team_name", team_id)
        self._attr_name = f"Nächstes Spiel {team_name}"
        self._attr_unique_id = f"handball_next_match_{team_id}"
        self._attr_icon = "mdi:calendar-clock"

    @property
    def state(self) -> str | None:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attributes

    def update_entity_picture(self, logo_url: str) -> None:
        """Update entity picture with opponent logo"""
        if logo_url and logo_url.strip():
            self._attr_entity_picture = logo_url

    async def async_update(self) -> None:
        matches = self.hass.data.get(DOMAIN, {}).get(self._team_id, {}).get("matches", [])
        if not matches:
            self._state = "Keine Spiele verfügbar"
            self._attributes = {}
            return

        next_match_info = get_next_match_info(matches)
        if not next_match_info:
            self._state = "Kein nächstes Spiel"
            self._attributes = {}
            self._attr_entity_picture = None
            return

        # Determine if home or away game
        match_data = self._find_match_by_id(matches, next_match_info["id"])
        if not match_data:
            return

        is_home_game = match_data["homeTeam"]["id"] == self._team_id
        opponent_team = match_data["awayTeam"] if is_home_game else match_data["homeTeam"]
        own_team = match_data["homeTeam"] if is_home_game else match_data["awayTeam"]

        # Set state with vs/@ prefix
        prefix = "vs" if is_home_game else "@"
        self._state = f"{prefix} {opponent_team['name']}"

        # Get opponent logo
        opponent_logo = opponent_team.get("logo")
        if opponent_logo:
            opponent_logo = normalize_logo_url(opponent_logo)
            self.update_entity_picture(opponent_logo)
        else:
            self._attr_entity_picture = None

        # Set detailed attributes
        self._attributes = {
            "match_id": next_match_info["id"],
            "opponent": opponent_team["name"],
            "opponent_logo": opponent_logo,
            "own_team": own_team["name"],
            "is_home_game": is_home_game,
            "location": "Zuhause" if is_home_game else "Auswärts",
            "starts_at": next_match_info["starts_at"],
            "starts_at_formatted": next_match_info["starts_at_formatted"],
            "starts_at_local": next_match_info["starts_at_local"],
            "field": next_match_info["field"],
            "days_until_match": self._calculate_days_until_match(next_match_info["starts_at"])
        }

    def _find_match_by_id(self, matches: list, match_id: str) -> Optional[dict]:
        """Find match by ID in matches list"""
        for match in matches:
            if match.get("id") == match_id:
                return match
        return None

    def _calculate_days_until_match(self, starts_at: int) -> int:
        """Calculate days until match"""
        try:
            match_time = datetime.fromtimestamp(starts_at / 1000, tz=timezone.utc)
            now = datetime.now(timezone.utc)
            delta = match_time - now
            return max(0, delta.days)
        except Exception:
            return 0
