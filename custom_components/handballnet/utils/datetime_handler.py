from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from ..const import GAME_DURATION_HOURS, DATE_FORMAT_UTC, DATE_FORMAT_LOCAL

class DateTimeHandler:
    """Handler für DateTime-Operationen im Handball-Kontext"""

    def __init__(self, game_duration_hours: int = GAME_DURATION_HOURS):
        self.game_duration_hours = game_duration_hours

    def timestamp_to_datetime(self, timestamp: int) -> Optional[datetime]:
        """Convert timestamp to UTC datetime"""
        if not isinstance(timestamp, int) or timestamp <= 0:
            return None
        try:
            return datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
        except (ValueError, OSError):
            return None

    def format_for_display(self, dt_or_timestamp) -> Dict[str, str]:
        """Format datetime or timestamp for display in attributes"""
        if isinstance(dt_or_timestamp, int):
            dt = self.timestamp_to_datetime(dt_or_timestamp)
            if not dt:
                return {"formatted": "Invalid timestamp", "local": "Invalid timestamp"}
        elif isinstance(dt_or_timestamp, datetime):
            dt = dt_or_timestamp
        else:
            return {"formatted": "Invalid input", "local": "Invalid input"}

        return {
            "formatted": dt.strftime(DATE_FORMAT_UTC),
            "local": dt.astimezone().strftime(DATE_FORMAT_LOCAL)
        }

    def is_game_live(self, start_timestamp: int, now: Optional[datetime] = None) -> bool:
        """Check if a game is currently live"""
        if now is None:
            now = datetime.now(timezone.utc)

        start_dt = self.timestamp_to_datetime(start_timestamp)
        if not start_dt:
            return False

        end_dt = start_dt + timedelta(hours=self.game_duration_hours)
        return start_dt <= now <= end_dt