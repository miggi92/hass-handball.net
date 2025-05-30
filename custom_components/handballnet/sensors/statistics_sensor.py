from typing import Any, Dict, List
from .base_sensor import HandballBaseSensor
from ..const import DOMAIN
import logging

_LOGGER = logging.getLogger(__name__)

class HandballStatisticsSensor(HandballBaseSensor):
    def __init__(self, hass, entry, team_id):
        super().__init__(hass, entry, team_id)
        self._state = None
        self._attributes = {}
        self._attr_name = f"Handball Statistiken {team_id}"
        self._attr_unique_id = f"handball_statistics_{team_id}"
        self._attr_icon = "mdi:chart-line"

    @property
    def state(self) -> str | None:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attributes

    async def async_update(self) -> None:
        matches = self.hass.data.get(DOMAIN, {}).get(self._team_id, {}).get("matches", [])
        if not matches:
            self._state = "Keine Daten verfügbar"
            self._attributes = {}
            return

        # Berechne Statistiken
        stats = self._calculate_statistics(matches)
        
        # Setze State als Gesamtbilanz
        total_games = stats["total"]["games_played"]
        total_wins = stats["total"]["wins"]
        if total_games > 0:
            win_percentage = round((total_wins / total_games) * 100, 1)
            self._state = f"{total_wins}/{total_games} Siege ({win_percentage}%)"
        else:
            self._state = "Keine Spiele gespielt"

        self._attributes = stats

    def _calculate_statistics(self, matches: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Berechne detaillierte Statistiken"""
        # Initialisiere Zähler
        stats = {
            "total": {"games_played": 0, "wins": 0, "draws": 0, "losses": 0, "goals_scored": 0, "goals_conceded": 0},
            "home": {"games_played": 0, "wins": 0, "draws": 0, "losses": 0, "goals_scored": 0, "goals_conceded": 0},
            "away": {"games_played": 0, "wins": 0, "draws": 0, "losses": 0, "goals_scored": 0, "goals_conceded": 0}
        }

        # Analysiere jedes Spiel
        for match in matches:
            # Nur gespielte Spiele (mit Ergebnis) berücksichtigen
            if not self._is_match_played(match):
                continue

            is_home_game = match["homeTeam"]["id"] == self._team_id
            location = "home" if is_home_game else "away"
            
            # Hole Tore
            if is_home_game:
                own_goals = match.get("homeGoals", 0)
                opponent_goals = match.get("awayGoals", 0)
            else:
                own_goals = match.get("awayGoals", 0)
                opponent_goals = match.get("homeGoals", 0)

            # Aktualisiere Statistiken
            for category in ["total", location]:
                stats[category]["games_played"] += 1
                stats[category]["goals_scored"] += own_goals
                stats[category]["goals_conceded"] += opponent_goals

                # Bestimme Spielergebnis
                if own_goals > opponent_goals:
                    stats[category]["wins"] += 1
                elif own_goals == opponent_goals:
                    stats[category]["draws"] += 1
                else:
                    stats[category]["losses"] += 1

        # Berechne prozentuale Werte und Durchschnitte
        return self._calculate_percentages_and_averages(stats)

    def _is_match_played(self, match: Dict[str, Any]) -> bool:
        """Prüfe ob das Spiel bereits gespielt wurde"""
        # Spiel ist gespielt wenn es Tore gibt oder Status "finished"/"post" ist
        home_goals = match.get("homeGoals")
        away_goals = match.get("awayGoals")
        state = match.get("state", "").lower()
        
        return (
            (home_goals is not None and away_goals is not None) or
            state in ["finished", "post", "ended"]
        )

    def _calculate_percentages_and_averages(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Berechne Prozentuale Werte und Durchschnitte"""
        result = {}
        
        for location in ["total", "home", "away"]:
            location_stats = stats[location]
            games = location_stats["games_played"]
            
            if games > 0:
                # Prozentuale Werte
                win_percentage = round((location_stats["wins"] / games) * 100, 1)
                draw_percentage = round((location_stats["draws"] / games) * 100, 1)
                loss_percentage = round((location_stats["losses"] / games) * 100, 1)
                
                # Durchschnittswerte
                avg_goals_scored = round(location_stats["goals_scored"] / games, 2)
                avg_goals_conceded = round(location_stats["goals_conceded"] / games, 2)
                goal_difference = location_stats["goals_scored"] - location_stats["goals_conceded"]
                avg_goal_difference = round(goal_difference / games, 2)
                
                result[location] = {
                    **location_stats,
                    "win_percentage": win_percentage,
                    "draw_percentage": draw_percentage,
                    "loss_percentage": loss_percentage,
                    "avg_goals_scored": avg_goals_scored,
                    "avg_goals_conceded": avg_goals_conceded,
                    "goal_difference": goal_difference,
                    "avg_goal_difference": avg_goal_difference,
                    "points": location_stats["wins"] * 2 + location_stats["draws"]  # Handball: 2 Punkte pro Sieg, 1 pro Unentschieden
                }
            else:
                # Keine Spiele gespielt
                result[location] = {
                    **location_stats,
                    "win_percentage": 0.0,
                    "draw_percentage": 0.0,
                    "loss_percentage": 0.0,
                    "avg_goals_scored": 0.0,
                    "avg_goals_conceded": 0.0,
                    "goal_difference": 0,
                    "avg_goal_difference": 0.0,
                    "points": 0
                }

        # Zusätzliche interessante Statistiken
        total_stats = result["total"]
        if total_stats["games_played"] > 0:
            result["additional"] = {
                "home_advantage": round(result["home"]["win_percentage"] - result["away"]["win_percentage"], 1),
                "strongest_location": "Zuhause" if result["home"]["win_percentage"] > result["away"]["win_percentage"] else "Auswärts",
                "most_productive_location": "Zuhause" if result["home"]["avg_goals_scored"] > result["away"]["avg_goals_scored"] else "Auswärts",
                "form_last_5": self._get_last_5_form(stats)
            }
        else:
            result["additional"] = {
                "home_advantage": 0.0,
                "strongest_location": "Unbekannt",
                "most_productive_location": "Unbekannt",
                "form_last_5": "Keine Daten"
            }

        return result

    def _get_last_5_form(self, original_stats: Dict[str, Any]) -> str:
        """Ermittle die Form der letzten 5 Spiele"""
        matches = self.hass.data.get(DOMAIN, {}).get(self._team_id, {}).get("matches", [])
        
        # Sortiere Spiele nach Datum (neueste zuerst) und nehme nur gespielte
        played_matches = [m for m in matches if self._is_match_played(m)]
        played_matches.sort(key=lambda x: x.get("startsAt", 0), reverse=True)
        
        last_5 = played_matches[:5]
        form = []
        
        for match in last_5:
            is_home_game = match["homeTeam"]["id"] == self._team_id
            
            if is_home_game:
                own_goals = match.get("homeGoals", 0)
                opponent_goals = match.get("awayGoals", 0)
            else:
                own_goals = match.get("awayGoals", 0)
                opponent_goals = match.get("homeGoals", 0)
            
            if own_goals > opponent_goals:
                form.append("S")  # Sieg
            elif own_goals == opponent_goals:
                form.append("U")  # Unentschieden
            else:
                form.append("N")  # Niederlage
        
        return "".join(form) if form else "Keine Daten"
