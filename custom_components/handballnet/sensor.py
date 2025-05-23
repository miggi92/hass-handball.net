from homeassistant.helpers.entity import Entity
import requests
import datetime

class HandballNetSensor(Entity):
    def __init__(self, team_id):
        self._team_id = team_id
        self._state = None
        self._attributes = {}

    def update(self):
        url = f"https://www.handball.net/a/sportdata/1/teams/{self._team_id}/schedule"
        try:
            response = requests.get(url)
            data = response.json()

            matches = data.get("data", [])
            team_name = None
            played_games = []

            for match in matches:
                if not team_name:
                    # Teamname aus dem ersten Spiel extrahieren
                    if match.get("homeTeam", {}).get("id") == self._team_id:
                        team_name = match["homeTeam"]["name"]
                    elif match.get("awayTeam", {}).get("id") == self._team_id:
                        team_name = match["awayTeam"]["name"]

                if match["state"] == "Post":
                    played_games.append(match)

            last_game = played_games[-1] if played_games else None

            self._state = f"{team_name}: {len(matches)} Spiele"
            self._attributes = {
                "anzahl_spiele": len(matches),
                "letztes_spiel": self._parse_game_summary(last_game) if last_game else "Kein Spiel verfügbar",
            }

        except Exception as e:
            self._state = "Fehler"
            self._attributes = {"error": str(e)}

    def _parse_game_summary(self, game):
        date = datetime.datetime.fromtimestamp(game["startsAt"] / 1000).strftime("%d.%m.%Y %H:%M")
        result = f"{game['homeTeam']['name']} {game['homeGoals']} : {game['awayGoals']} {game['awayTeam']['name']}"
        return f"{date} – {result}"

    @property
    def name(self):
        return f"Handball {self._team_id}"

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        return self._attributes
