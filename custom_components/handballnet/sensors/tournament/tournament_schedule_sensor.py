"""Tournament schedule sensor: whole league schedule grouped by matchday."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from .base_sensor import HandballBaseSensor

_RECENT_RESULTS = 21  # roughly the last three matchdays
_UPCOMING = 21


def _compact(match: dict[str, Any], with_result: bool = True) -> dict[str, Any]:
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


def _group_matchdays(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group matches by matchday.

    Uses the API's round number when every match has one; otherwise falls back
    to ISO calendar weeks (postponed games then appear in the week they are
    actually played).
    """
    dated = [m for m in matches if m.get("startsAt")]
    use_rounds = bool(dated) and all(isinstance(m.get("round"), int) for m in dated)

    groups: dict[Any, list[dict[str, Any]]] = {}
    for match in dated:
        if use_rounds:
            key = match["round"]
        else:
            dt = datetime.fromtimestamp(match["startsAt"] / 1000, tz=timezone.utc)
            iso = dt.isocalendar()
            key = (iso[0], iso[1])
        groups.setdefault(key, []).append(match)

    matchdays = []
    for key in sorted(groups):
        items = sorted(groups[key], key=lambda m: m["startsAt"])
        label = f"Spieltag {key}" if use_rounds else f"KW {key[1]}"
        matchdays.append(
            {
                "label": label,
                "round": key if use_rounds else None,
                "start": items[0]["startsAt"],
                "end": items[-1]["startsAt"],
                "matches": [_compact(m) for m in items],
            }
        )
    return matchdays


class HandballTournamentScheduleSensor(HandballBaseSensor):
    """State = number of remaining matches; attributes = schedule by matchday."""

    # The schedule is large; keep it out of the recorder database.
    _unrecorded_attributes = frozenset(
        {"upcoming_matches", "recent_results", "matchdays"}
    )

    def __init__(self, coordinator, entry, tournament_id, api=None):
        super().__init__(coordinator, entry, tournament_id)
        self._tournament_id = tournament_id
        tournament_name = entry.data.get("tournament_name", tournament_id)
        self._attr_name = f"{tournament_name} Spielplan"
        self._attr_unique_id = f"handball_tournament_{tournament_id}_schedule"
        self._attr_icon = "mdi:calendar-text"

    def _matches(self) -> list[dict[str, Any]]:
        return self._get_tournament_bucket().get("matches", []) or []

    def _split(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        now_ms = time.time() * 1000
        matches = self._matches()
        upcoming = [m for m in matches if (m.get("startsAt") or 0) > now_ms]
        played = [m for m in matches if 0 < (m.get("startsAt") or 0) <= now_ms]
        return upcoming, played

    @property
    def state(self) -> int:
        return len(self._split()[0])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        upcoming, played = self._split()
        matchdays = _group_matchdays(self._matches())
        now_ms = time.time() * 1000
        # Current matchday: the first one whose typical (median) kick-off is
        # still ahead or at most 2 h ago. Using the median ignores single
        # postponed games, which would otherwise pin an early matchday.
        def _median_start(md: dict[str, Any]) -> float:
            starts = sorted(m.get("starts_at") or 0 for m in md["matches"])
            return starts[len(starts) // 2] if starts else 0

        current = next(
            (
                i
                for i, md in enumerate(matchdays)
                if _median_start(md) + 7_200_000 > now_ms
            ),
            max(len(matchdays) - 1, 0),
        )
        return {
            "total_matches": len(upcoming) + len(played),
            "played_matches": len(played),
            "remaining_matches": len(upcoming),
            "next_match_at": upcoming[0].get("startsAt") if upcoming else None,
            "current_matchday_index": current,
            "matchday_mode": "round"
            if matchdays and matchdays[0]["round"] is not None
            else "calendar_week",
            "matchdays": matchdays,
            "upcoming_matches": [_compact(m, False) for m in upcoming[:_UPCOMING]],
            "recent_results": [_compact(m) for m in played[-_RECENT_RESULTS:]][::-1],
        }
