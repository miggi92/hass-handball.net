from datetime import datetime, timezone
from typing import Any

from .base_sensor import HandballBaseSensor


class HandballTournamentRemainingTeamsSensor(HandballBaseSensor):
    """Show teams that are still active in a knockout tournament."""

    def __init__(self, coordinator, entry, tournament_id):
        super().__init__(coordinator, entry, tournament_id)
        self._tournament_id = tournament_id
        tournament_name = entry.data.get("tournament_name", tournament_id)
        self._attr_name = f"{tournament_name} Verbleibende Teams"
        self._attr_unique_id = f"handball_tournament_{tournament_id}_remaining_teams"
        self._attr_icon = "mdi:account-group"

    @property
    def state(self) -> int:
        return len(self._build_remaining_teams())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        tournament_bucket = self._get_tournament_bucket()
        tournament_info = tournament_bucket.get("tournament_info", {})
        matches = tournament_bucket.get("matches", [])
        remaining_teams = self._build_remaining_teams()

        return {
            "tournament_name": tournament_info.get("name", self._tournament_id),
            "total_matches": len(matches),
            "remaining_teams_count": len(remaining_teams),
            "remaining_teams": remaining_teams,
        }

    def _build_remaining_teams(self) -> list[dict[str, Any]]:
        matches = self._get_tournament_bucket().get("matches", [])
        if not matches:
            return []

        now_ts = datetime.now(timezone.utc).timestamp()
        team_index: dict[str, dict[str, Any]] = {}
        teams_with_future_match: set[str] = set()
        eliminated_teams: set[str] = set()

        for match in matches:
            home_team = match.get("homeTeam", {})
            away_team = match.get("awayTeam", {})
            home_id = home_team.get("id")
            away_id = away_team.get("id")
            start_ts_raw = match.get("startsAt")
            start_ts = start_ts_raw / 1000 if isinstance(start_ts_raw, int) else None

            for team in (home_team, away_team):
                team_id = team.get("id")
                if not team_id:
                    continue

                if team_id not in team_index:
                    team_index[team_id] = {
                        "team_id": team_id,
                        "team_name": team.get("name", team_id),
                        "team_logo": team.get("logo"),
                    }

            if start_ts is not None and start_ts > now_ts:
                if home_id:
                    teams_with_future_match.add(home_id)
                if away_id:
                    teams_with_future_match.add(away_id)

            home_goals = match.get("homeGoals")
            away_goals = match.get("awayGoals")
            if not isinstance(home_goals, int) or not isinstance(away_goals, int):
                continue

            if home_goals > away_goals and away_id:
                eliminated_teams.add(away_id)
            elif away_goals > home_goals and home_id:
                eliminated_teams.add(home_id)

        remaining_ids = {
            team_id
            for team_id in team_index
            if team_id in teams_with_future_match or team_id not in eliminated_teams
        }

        return sorted(
            (team_index[team_id] for team_id in remaining_ids),
            key=lambda item: item.get("team_name", ""),
        )
