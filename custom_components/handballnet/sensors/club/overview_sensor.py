from __future__ import annotations

from datetime import datetime
from typing import Any

from ..base_sensor import HandballBaseSensor
from ...const import CONF_CLUB_ID, CONF_TEAM_MAPPING, DOMAIN


class HandballClubOverviewSensor(HandballBaseSensor):
    def __init__(self, coordinator, entry):
        club_id = entry.data.get(CONF_CLUB_ID, entry.entry_id)
        super().__init__(coordinator, entry, club_id)
        self._club_id = club_id
        self._club_name = entry.data.get("club_name") or club_id
        self._team_mapping = entry.data.get(CONF_TEAM_MAPPING, {})

        self._attr_name = f"{self._club_name} Verein"
        self._attr_unique_id = f"{entry.entry_id}_club_overview"
        self._attr_icon = "mdi:shield-account"
        self._attr_device_info = self._create_device_info(
            identifiers={(DOMAIN, self._club_id)},
            name=self._club_name,
            model="Handball Club",
        )

    @property
    def state(self) -> int:
        return len(self._team_mapping)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        teams = self._build_team_summaries()
        next_matches = sorted(
            [
                {
                    "team_id": team["team_id"],
                    "team_name": team["team_name"],
                    "team_logo": team.get("team_logo"),
                    "match": team["next_match"],
                }
                for team in teams
                if team.get("next_match")
            ],
            key=lambda item: item["match"].get("starts_at") or 0,
        )

        return {
            "club_id": self._club_id,
            "club_name": self._club_name,
            "team_count": len(teams),
            "teams": teams,
            "next_matches": next_matches,
        }

    def _build_team_summaries(self) -> list[dict[str, Any]]:
        teams: list[dict[str, Any]] = []
        team_buckets = (self.coordinator.data or {}).get("teams", {})

        for configured_team_name, team_id in self._team_mapping.items():
            team_bucket = team_buckets.get(team_id, {})
            team_name = team_bucket.get("team_name") or configured_team_name
            teams.append(
                {
                    "team_id": team_id,
                    "team_name": team_name,
                    "team_logo": team_bucket.get("team_logo_url"),
                    "next_match": team_bucket.get("next_match"),
                    "last_match": team_bucket.get("last_match"),
                    "table_position": team_bucket.get("table_position"),
                    "is_live": team_bucket.get("is_live", False),
                }
            )

        return sorted(teams, key=self._team_sort_key)

    def _team_sort_key(self, team: dict[str, Any]) -> tuple[datetime, str]:
        next_match = team.get("next_match") or {}
        starts_at = next_match.get("starts_at")
        if isinstance(starts_at, int):
            return (datetime.fromtimestamp(starts_at / 1000), team.get("team_name", ""))
        return (datetime.max, team.get("team_name", ""))