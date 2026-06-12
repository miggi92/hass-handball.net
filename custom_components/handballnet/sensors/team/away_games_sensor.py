from typing import Any, Optional
from .base_sensor import HandballBaseSensor
from ...utils import HandballNetUtils

class HandballAuswaertsspielSensor(HandballBaseSensor):
    def __init__(self, coordinator, entry, team_id, team_name):
        super().__init__(coordinator, entry, team_id, team_name)
        self.utils = HandballNetUtils()
        self._team_id = team_id

        display_name = self._resolve_display_name(team_name)
        self._attr_name = f"{display_name} Auswärtsspiel"
        self._attr_unique_id = self._build_unique_id("away_game")
        self._attr_icon = "mdi:handball"

    @property
    def state(self) -> Optional[str]:
        match = self._get_next_away_match()
        if not match:
            return "Kein Auswärtsspiel geplant"

        opponent = match.get("homeTeam", {}).get("name", "")
        time_formats = self.utils.format_datetime_for_display(match.get("startsAt"))
        return f"@ {opponent}" if opponent else time_formats["formatted"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        match = self._get_next_away_match()
        if not match:
            return {}

        time_formats = self.utils.format_datetime_for_display(match.get("startsAt"))
        return {
            "opponent": match.get("homeTeam", {}).get("name", ""),
            "home_team": match.get("homeTeam", {}).get("name", ""),
            "away_team": match.get("awayTeam", {}).get("name", ""),
            "location": match.get("field", {}).get("name", ""),
            "startsAt": match.get("startsAt"),
            "starts_at_local": time_formats["local"],
            "starts_at_formatted": time_formats["formatted"],
            "competition": match.get("tournament", {}).get("name", ""),
            "match_id": match.get("id"),
            "match_date": time_formats["formatted"],
        }

    def update_entity_picture(self, logo_url: str) -> None:
        if logo_url:
            self._attr_entity_picture = self.utils.normalize_logo_url(logo_url)

    def _get_next_away_match(self) -> dict[str, Any] | None:
        matches = self._get_team_bucket().get("matches", [])
        for match in matches:
            if match.get("isAway"):
                return match
        return None