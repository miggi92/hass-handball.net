"""Tournament schedule sensor: remaining matches of the whole league."""
from __future__ import annotations

import time
from typing import Any

from .base_sensor import HandballBaseSensor

_RECENT_RESULTS = 21  # roughly the last three matchdays


def _compact(match: dict[str, Any], with_result: bool) -> dict[str, Any]:
    home = match.get("homeTeam") or {}
    away = match.get("awayTeam") or {}
    item = {
        "id": match.get("id"),
        "starts_at": match.get("startsAt"),
        "home": home.get("name"),
        "away": away.get("name"),
        "field": (match.get("field") or {}).get("name"),
    }
    if with_result:
        item["home_goals"] = match.get("homeGoals")
        item["away_goals"] = match.get("awayGoals")
    return item


class HandballTournamentScheduleSensor(HandballBaseSensor):
    """State = number of remaining matches; attributes = full remaining schedule."""

    # The schedule can be large; keep it out of the recorder database.
    _unrecorded_attributes = frozenset({"upcoming_matches", "recent_results"})

    def __init__(self, coordinator, entry, tournament_id, api=None):
        super().__init__(coordinator, entry, tournament_id)
        self._tournament_id = tournament_id
        tournament_name = entry.data.get("tournament_name", tournament_id)
        self._attr_name = f"{tournament_name} Spielplan"
        self._attr_unique_id = f"handball_tournament_{tournament_id}_schedule"
        self._attr_icon = "mdi:calendar-text"

    def _split(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        now_ms = time.time() * 1000
        matches = self._get_tournament_bucket().get("matches", []) or []
        upcoming = [m for m in matches if (m.get("startsAt") or 0) > now_ms]
        played = [m for m in matches if 0 < (m.get("startsAt") or 0) <= now_ms]
        return upcoming, played

    @property
    def state(self) -> int:
        return len(self._split()[0])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        upcoming, played = self._split()
        return {
            "total_matches": len(upcoming) + len(played),
            "played_matches": len(played),
            "remaining_matches": len(upcoming),
            "next_match_at": upcoming[0].get("startsAt") if upcoming else None,
            "upcoming_matches": [_compact(m, False) for m in upcoming],
            "recent_results": [
                _compact(m, True) for m in played[-_RECENT_RESULTS:]
            ][::-1],
        }
