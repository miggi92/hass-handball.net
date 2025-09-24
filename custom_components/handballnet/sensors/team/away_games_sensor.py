from datetime import datetime, timezone
from typing import Any, Optional
from .base_sensor import HandballBaseSensor
from ...const import DOMAIN
from ...utils import HandballNetUtils

class HandballAuswaertsspielSensor(HandballBaseSensor):
    def __init__(self, hass, entry, team_id):
        super().__init__(hass, entry, team_id)
        self.utils = HandballNetUtils()
        self._team_id = team_id  # Explicitly set _team_id
        self._state = None
        self._attributes = {}

        # Use team name from config if available, fallback to team_id
        team_name = entry.data.get("team_name", team_id)
        self._attr_name = f"{team_name} Auswärtsspiel"
        self._attr_unique_id = f"handball_team_{team_id}_away_game"
        self._attr_icon = "mdi:handball"

    @property
    def state(self) -> Optional[str]:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attributes

    def update_entity_picture(self, logo_url: str) -> None:
        """Update entity picture with logo URL"""
        if logo_url:
            self._attr_entity_picture = self.utils.normalize_logo_url(logo_url)

    async def async_update(self) -> None:
        """Update the sensor state and attributes."""
        now_ts = datetime.now(timezone.utc).timestamp()
        matches = self.hass.data.get(DOMAIN, {}).get(self._team_id, {}).get("matches", [])

        # Find the next away match
        next_away_match = None
        for match in matches:
            if match.get("isAway", False) and match.get("startsAt", 0) / 1000 > now_ts:
                next_away_match = match
                break

        if next_away_match:
            # Get the timestamp and format it properly
            starts_at = next_away_match.get("startsAt")
            time_formats = self.utils.format_datetime_for_display(starts_at)

            # Determine opponent team (for away match, opponent is home team)
            home_team = next_away_match.get("homeTeam", {}).get("name", "")
            away_team = next_away_match.get("awayTeam", {}).get("name", "")
            opponent = home_team  # For away match, opponent is home team

            # Set opponent logo as entity picture
            opponent_logo = next_away_match.get("homeTeam", {}).get("logo")
            if opponent_logo:
                self.update_entity_picture(opponent_logo)

            # Set opponent name as state
            self._state = f"@ {opponent}" if opponent else time_formats["formatted"]
            self._attributes = {
                "opponent": opponent,
                "home_team": home_team,
                "away_team": away_team,
                "location": next_away_match.get("field", {}).get("name", ""),
                "startsAt": starts_at,
                "starts_at_local": time_formats["local"],
                "starts_at_formatted": time_formats["formatted"],
                "competition": next_away_match.get("tournament", {}).get("name", ""),
                "match_id": next_away_match.get("id"),
                "match_date": time_formats["formatted"]
            }
        else:
            self._state = "Kein Auswärtsspiel geplant"
            self._attributes = {}
            # Clear entity picture when no away game
            self._attr_entity_picture = None