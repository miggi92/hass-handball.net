from typing import Any, Optional
from .base_sensor import HandballBaseSensor
from ...utils import HandballNetUtils
import logging

_LOGGER = logging.getLogger(__name__)


class HandballNextMatchSensor(HandballBaseSensor):
    def __init__(self, coordinator, entry, team_id, team_name, api=None):
        super().__init__(coordinator, entry, team_id, team_name)
        self.utils = HandballNetUtils()
        self._team_id = team_id

        display_name = self._resolve_display_name(team_name)
        self._attr_name = f"{display_name} Nächstes Spiel"
        self._attr_unique_id = self._build_unique_id("next_match")
        self._attr_icon = "mdi:calendar-clock"

    @property
    def state(self) -> str | None:
        next_match = self._get_team_bucket().get("next_match")
        if not next_match:
            return "Kein nächstes Spiel"
        opponent = next_match.get("opponent", {"name": "Unbekannter Gegner"})
        return opponent["name"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        next_match = self._get_team_bucket().get("next_match")
        if not next_match:
            return {}

        return {
            "match_date": next_match.get("starts_at_formatted"),
            "match_time": next_match.get("starts_at_local"),
            "home_team": next_match.get("home_team"),
            "away_team": next_match.get("away_team"),
            "field": next_match.get("field"),
            "starts_at": next_match.get("starts_at"),
        }
