from datetime import datetime, timezone, timedelta
from typing import Any, Optional
import logging
from homeassistant.helpers.event import async_call_later
from .base_sensor import HandballBaseSensor
from ..const import DOMAIN, CONF_UPDATE_INTERVAL_LIVE, DEFAULT_UPDATE_INTERVAL_LIVE
from ..api import HandballNetAPI

_LOGGER = logging.getLogger(__name__)

class HandballLiveTickerEventsSensor(HandballBaseSensor):
    def __init__(self, hass, entry, team_id, api: HandballNetAPI):
        super().__init__(hass, entry, team_id)
        self._api = api
        self._entry = entry
        
        # Use team name from config if available, fallback to team_id
        team_name = entry.data.get("team_name", team_id)
        self._attr_name = f"{team_name} Live Ticker Events"
        self._attr_unique_id = f"handball_{team_id}_live_ticker_events"
        self._attr_icon = "mdi:television-play"
        self._attr_should_poll = False
        self._state = "Kein Live-Spiel"
        self._attributes = {}
        self._update_handle = None

    @property
    def state(self) -> str:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attributes

    def get_current_live_game(self) -> Optional[dict]:
        """Find currently running game"""
        matches = self.hass.data.get(DOMAIN, {}).get(self._team_id, {}).get("matches", [])
        now = datetime.now(timezone.utc)
        
        for match in matches:
            ts = match.get("startsAt")
            if not isinstance(ts, int):
                continue
            try:
                start = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
                end = start + timedelta(hours=2)
            except Exception:
                continue
            
            if start <= now <= end:
                return match
        return None

    def is_live_game_active(self) -> bool:
        """Check if there's currently a live game"""
        return self.get_current_live_game() is not None

    async def async_update_live_ticker(self) -> None:
        """Update live ticker data"""
        current_game = self.get_current_live_game()
        
        if not current_game:
            self._state = "Kein Live-Spiel"
            self._attributes = {
                "game_state": "no_live_game",
                "last_updated": datetime.now().isoformat()
            }
            # Schedule next check with normal interval when no live game
            await self._schedule_next_update(is_live=False)
            return

        game_id = current_game.get("id")
        if not game_id:
            _LOGGER.warning("No game ID found for current game")
            await self._schedule_next_update(is_live=True)
            return

        try:
            live_data = await self._api.get_live_ticker(game_id)
            if not live_data:
                _LOGGER.warning("No live ticker data received for game %s", game_id)
                await self._schedule_next_update(is_live=True)
                return

            summary = live_data.get("summary", {})
            events = live_data.get("events", [])
            
            # Get current score and game state
            home_goals = summary.get("homeGoals", 0)
            away_goals = summary.get("awayGoals", 0)
            game_state = summary.get("state", "Unknown")
            home_team = summary.get("homeTeam", {}).get("name", "Home")
            away_team = summary.get("awayTeam", {}).get("name", "Away")
            
            # Current state as text
            if game_state == "Live":
                self._state = f"🔴 LIVE: {home_team} {home_goals}:{away_goals} {away_team}"
            elif game_state == "Post":
                self._state = f"✅ Beendet: {home_team} {home_goals}:{away_goals} {away_team}"
            elif game_state == "Pre":
                self._state = f"⏰ Bald: {home_team} vs {away_team}"
            else:
                self._state = f"{home_team} vs {away_team}"

            # Get latest events (last 10) with formatted timestamps
            latest_events = []
            for event in events[:10]:  # First 10 events (newest first)
                timestamp = event.get("timestamp", 0)
                event_data = {
                    "type": event.get("type", "Unknown"),
                    "time": event.get("time", ""),
                    "message": event.get("message", ""),
                    "score": event.get("score", ""),
                    "team": event.get("team", ""),
                    "timestamp": timestamp
                }
                
                # Add formatted timestamps if timestamp exists
                if timestamp and isinstance(timestamp, (int, float)) and timestamp > 0:
                    try:
                        event_time = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
                        event_data.update({
                            "timestamp_formatted": event_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
                            "timestamp_local": event_time.astimezone().strftime("%Y-%m-%d %H:%M:%S")
                        })
                    except Exception:
                        pass
                
                latest_events.append(event_data)

            # Get half-time scores
            home_goals_half = summary.get("homeGoalsHalf")
            away_goals_half = summary.get("awayGoalsHalf")
            
            # Format game start time
            starts_at = summary.get("startsAt")
            starts_at_formatted = None
            starts_at_local = None
            
            if starts_at and isinstance(starts_at, (int, float)) and starts_at > 0:
                try:
                    start_time = datetime.fromtimestamp(starts_at / 1000, tz=timezone.utc)
                    starts_at_formatted = start_time.strftime("%Y-%m-%d %H:%M:%S UTC")
                    starts_at_local = start_time.astimezone().strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    pass

            self._attributes = {
                "game_id": game_id,
                "game_state": game_state,
                "home_team": home_team,
                "away_team": away_team,
                "home_goals": home_goals,
                "away_goals": away_goals,
                "home_goals_half": home_goals_half,
                "away_goals_half": away_goals_half,
                "field": summary.get("field", {}).get("name", ""),
                "starts_at": starts_at,
                "starts_at_formatted": starts_at_formatted,
                "starts_at_local": starts_at_local,
                "latest_events": latest_events,
                "total_events": len(events),
                "last_updated": datetime.now().isoformat(),
                "last_event": latest_events[0] if latest_events else None
            }

            # Schedule next update with live interval
            await self._schedule_next_update(is_live=True)

        except Exception as e:
            _LOGGER.error("Error updating live ticker for game %s: %s", game_id, e)
            self._state = "Fehler beim Laden"
            self._attributes = {
                "error": str(e),
                "last_updated": datetime.now().isoformat()
            }
            # Still schedule next update even on error
            await self._schedule_next_update(is_live=True)

    async def _schedule_next_update(self, is_live: bool = False) -> None:
        """Schedule the next update based on live status"""
        # Cancel existing update handle
        if self._update_handle:
            self._update_handle()
            self._update_handle = None

        # Get update interval
        if is_live:
            interval = self._entry.options.get(
                CONF_UPDATE_INTERVAL_LIVE, 
                self._entry.data.get(CONF_UPDATE_INTERVAL_LIVE, DEFAULT_UPDATE_INTERVAL_LIVE)
            )
        else:
            # Use longer interval when no live game (60 seconds to check for new games)
            interval = 60

        # Schedule next update
        async def next_update(now=None):
            await self.async_update_live_ticker()
            self.async_write_ha_state()

        self._update_handle = async_call_later(self.hass, interval, next_update)

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass, start the update cycle"""
        await super().async_added_to_hass()
        # Start initial update
        await self.async_update_live_ticker()
        self.async_write_ha_state()

    async def async_will_remove_from_hass(self) -> None:
        """When entity is removed, cancel scheduled updates"""
        if self._update_handle:
            self._update_handle()
            self._update_handle = None
        await super().async_will_remove_from_hass()
