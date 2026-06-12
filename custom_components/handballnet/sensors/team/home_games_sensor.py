from typing import Any, Optional
from .base_sensor import HandballBaseSensor
from ...utils import HandballNetUtils


class HandballHeimspielSensor(HandballBaseSensor):
    def __init__(self, coordinator, entry, team_id, team_name):
        super().__init__(coordinator, entry, team_id, team_name)
        self.utils = HandballNetUtils()
        self._team_id = team_id

        display_name = self._resolve_display_name(team_name)
        self._attr_name = f"{display_name} Heimspiel"
        self._attr_unique_id = self._build_unique_id("home_game")
        self._attr_icon = "mdi:home"

    @property
    def state(self) -> Optional[str]:
        match = self._get_next_home_match()
        if not match:
            return "Kein Heimspiel geplant"

        opponent = match.get("awayTeam", {}).get("name", "")
        time_formats = self.utils.format_datetime_for_display(match.get("startsAt"))
        return f"vs {opponent}" if opponent else time_formats["formatted"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        match = self._get_next_home_match()
        if not match:
            return {}

        time_formats = self.utils.format_datetime_for_display(match.get("startsAt"))
        return {
            "opponent": match.get("awayTeam", {}).get("name", ""),
            "home_team": match.get("homeTeam", {}).get("name", ""),
            "away_team": match.get("awayTeam", {}).get("name", ""),
            "location": match.get("field", {}).get("name", ""),
            "startsAt": match.get("startsAt"),
            "starts_at_local": time_formats["local"],
            "starts_at_formatted": time_formats["formatted"],
            "match_date": time_formats["formatted"],
        }

    def update_entity_picture(self, logo_url: str) -> None:
        if logo_url:
            self._attr_entity_picture = self.utils.normalize_logo_url(logo_url)

    def _get_next_home_match(self) -> dict[str, Any] | None:
        matches = self._get_team_bucket().get("matches", [])
        for match in matches:
            if match.get("isHomeMatch"):
                return match
        return None
