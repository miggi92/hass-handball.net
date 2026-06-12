from typing import Any, List, Dict
from .base_sensor import HandballBaseSensor
from ...utils import HandballNetUtils

class HandballTournamentTableSensor(HandballBaseSensor):
    def __init__(self, coordinator, entry, tournament_id, api=None):
        super().__init__(coordinator, entry, tournament_id)
        self.utils = HandballNetUtils()
        self._tournament_id = tournament_id

        tournament_name = entry.data.get("tournament_name", tournament_id)
        self._attr_name = f"{tournament_name} Tabelle"
        self._attr_unique_id = f"handball_tournament_{tournament_id}_table"
        self._attr_icon = "mdi:trophy"

    @property
    def state(self) -> str | None:
        tournament_bucket = self._get_tournament_bucket()
        table_rows = tournament_bucket.get("table_rows", [])
        if not table_rows:
            return "Keine Tabellendaten verfügbar"

        leader = table_rows[0]
        return f"{leader['team_name']} führt mit {leader['points']} Punkten"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        tournament_bucket = self._get_tournament_bucket()
        table_rows = tournament_bucket.get("table_rows", [])
        if not table_rows:
            return {"tournament_name": self._tournament_id, "tournament_acronym": "", "organization": "", "total_teams": 0, "table": [], "leader": None, "last_place": None}

        tournament_info = tournament_bucket.get("tournament_info", {})
        return {
            "tournament_name": tournament_info.get("name", self._tournament_id),
            "tournament_acronym": tournament_info.get("acronym", ""),
            "organization": tournament_info.get("organization", ""),
            "total_teams": len(table_rows),
            "table": table_rows[:10],
            "leader": table_rows[0],
            "last_place": table_rows[-1],
        }