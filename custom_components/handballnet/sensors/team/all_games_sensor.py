from typing import Any
from .base_sensor import HandballBaseSensor
from ...utils import HandballNetUtils

class HandballAllGamesSensor(HandballBaseSensor):
    def __init__(self, coordinator, entry, team_id, team_name, api=None):
        super().__init__(coordinator, entry, team_id, team_name)
        self.utils = HandballNetUtils()
        self._team_id = team_id

        club_name = entry.data.get("club_name")
        display_name = f"{club_name} {team_name}" if club_name else team_name
        self._attr_name = f"{display_name} Alle Spiele"
        self._attr_unique_id = self._build_unique_id("all_games")
        self._attr_icon = "mdi:calendar"

    @property
    def state(self) -> str | None:
        team_bucket = self._get_team_bucket()
        matches = team_bucket.get("matches", [])
        if not matches:
            return "Keine Spiele verfügbar"

        next_match = team_bucket.get("next_match") or self.utils.get_next_match_info(matches)
        return f"Nächstes Spiel: {next_match['opponent']['name']}" if next_match else "Kein nächstes Spiel"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        team_bucket = self._get_team_bucket()
        matches = team_bucket.get("matches", [])
        next_match = team_bucket.get("next_match") or self.utils.get_next_match_info(matches)
        last_match = team_bucket.get("last_match") or self.utils.get_last_match_info(matches)

        if not matches:
            return {"next_match": None, "last_match": None, "total_matches": 0, "upcoming_matches": [], "recent_matches": []}

        return {
            "next_match": next_match,
            "last_match": last_match,
            "total_matches": len(matches),
            "upcoming_matches": [match for match in matches if match.get("startsAt", 0) > 0][:5],
            "recent_matches": [match for match in matches if match.get("state") == "Post"][-5:],
        }