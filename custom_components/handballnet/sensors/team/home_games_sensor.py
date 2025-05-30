from datetime import datetime, timezone
from typing import Any, Optional
from ..base_sensor import HandballBaseSensor
from ...const import DOMAIN
from ...utils import format_datetime_for_display

class HandballHeimspielSensor(HandballBaseSensor):
    def __init__(self, hass, entry, team_id):
        super().__init__(hass, entry, team_id)
        self._state = None
        self._attributes = {}
        self._attr_name = f"{team_id} Heimspiel"
        self._attr_unique_id = f"handball_team_{team_id}_home_game"
        self._attr_icon = "mdi:home"

    @property
    def state(self) -> Optional[str]:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attributes

    async def async_update(self) -> None:
        matches = self.hass.data.get(DOMAIN, {}).get(self._team_id, {}).get("matches", [])
        now_ts = datetime.now(timezone.utc).timestamp()

        next_home_game = None
        for match in matches:
            if match.get("isHomeMatch") and match.get("startsAt", 0) / 1000 > now_ts:
                next_home_game = match
                break

        if next_home_game:
            self._state = format_datetime_for_display(next_home_game.get("startsAt"))
            self._attributes = {
                "opponent": next_home_game.get("opponent"),
                "location": next_home_game.get("location"),
                "startsAt": next_home_game.get("startsAt"),
            }
        else:
            self._state = "Kein Heimspiel geplant"
            self._attributes = {}