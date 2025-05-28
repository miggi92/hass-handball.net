from datetime import datetime, timezone
from typing import Any
from .base_sensor import HandballBaseSensor
from ..const import DOMAIN
from ..api import HandballNetAPI


class HandballAllGamesSensor(HandballBaseSensor):
    def __init__(self, hass, entry, team_id, api: HandballNetAPI):
        super().__init__(hass, entry, team_id)
        self._api = api
        self._state = None
        self._attributes = {}
        self._attr_name = f"Alle Spiele {team_id}"
        self._attr_unique_id = f"handball_all_games_{team_id}"

    @property
    def state(self) -> str | None:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attributes

    async def async_update(self) -> None:
        matches = await self._api.get_team_schedule(self._team_id)
        if matches is None:
            return

        heimspiele = []
        auswaertsspiele = []
        team_name = None
        next_match = None
        last_match = None
        now = datetime.now(timezone.utc)

        for match in matches:
            if match["homeTeam"]["id"] == self._team_id:
                heimspiele.append(match)
                team_name = match["homeTeam"]["name"]
            elif match["awayTeam"]["id"] == self._team_id:
                auswaertsspiele.append(match)
                team_name = match["awayTeam"]["name"]

        # Update device name for all sensors if we have team name
        if team_name:
            self.update_device_name(team_name)
            # Update device name for other sensors in the same device
            if hasattr(self.hass.data[DOMAIN][self._team_id], 'sensors'):
                for sensor in self.hass.data[DOMAIN][self._team_id]['sensors']:
                    sensor.update_device_name(team_name)

        # Find next and last match
        for match in sorted(matches, key=lambda x: x.get("startsAt", 0)):
            match_time = datetime.fromtimestamp(match.get("startsAt", 0) / 1000, tz=timezone.utc)
            if match_time > now and next_match is None:
                next_match = {
                    "id": match.get("id"),
                    "home_team": match.get("homeTeam", {}).get("name"),
                    "away_team": match.get("awayTeam", {}).get("name"),
                    "starts_at": match.get("startsAt"),
                    "starts_at_formatted": match_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "starts_at_local": match_time.astimezone().strftime("%Y-%m-%d %H:%M:%S"),
                    "field": match.get("field", {}).get("name")
                }
            elif match_time <= now:
                last_match_time = datetime.fromtimestamp(match.get("startsAt", 0) / 1000, tz=timezone.utc)
                last_match = {
                    "id": match.get("id"),
                    "home_team": match.get("homeTeam", {}).get("name"),
                    "away_team": match.get("awayTeam", {}).get("name"),
                    "starts_at": match.get("startsAt"),
                    "starts_at_formatted": last_match_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    "starts_at_local": last_match_time.astimezone().strftime("%Y-%m-%d %H:%M:%S"),
                    "home_goals": match.get("homeGoals"),
                    "away_goals": match.get("awayGoals"),
                    "state": match.get("state")
                }

        self._state = f"{team_name} ({len(matches)} Spiele)"
        self._attributes = {
            "team_name": team_name,
            "total_games": len(matches),
            "home_games": len(heimspiele),
            "away_games": len(auswaertsspiele),
            "next_match": next_match,
            "last_match": last_match
        }

        self.hass.data[DOMAIN][self._team_id]["matches"] = matches
        self.hass.data[DOMAIN][self._team_id]["heimspiele"] = heimspiele
        self.hass.data[DOMAIN][self._team_id]["auswaertsspiele"] = auswaertsspiele
        self.hass.data[DOMAIN][self._team_id]["team_name"] = team_name
