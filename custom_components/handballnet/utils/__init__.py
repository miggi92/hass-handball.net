from .datetime_handler import DateTimeHandler
from .match_handler import MatchHandler
from .url_handler import URLHandler

class HandballNetUtils:
    """Zentrale Utilities-Klasse für handball.net Integration"""

    def __init__(self):
        self.datetime = DateTimeHandler()
        self.matches = MatchHandler()
        self.urls = URLHandler()

# Für Backward-Kompatibilität - alte Funktionen beibehalten
def timestamp_to_datetime(timestamp: int):
    return HandballNetUtils().datetime.timestamp_to_datetime(timestamp)

def format_datetime_for_display(dt_or_timestamp):
    return HandballNetUtils().datetime.format_for_display(dt_or_timestamp)

def is_game_live(start_timestamp: int, now=None):
    return HandballNetUtils().datetime.is_game_live(start_timestamp, now)

def get_next_match_info(matches: list, now=None):
    return HandballNetUtils().matches.get_next_match(matches, now)

def get_last_match_info(matches: list, now=None):
    return HandballNetUtils().matches.get_last_match(matches, now)

def normalize_logo_url(logo_url: str):
    return HandballNetUtils().urls.normalize_logo_url(logo_url)

__all__ = [
    "HandballNetUtils",
    "DateTimeHandler",
    "MatchHandler",
    "URLHandler",
    # Backward compatibility
    "timestamp_to_datetime",
    "format_datetime_for_display",
    "is_game_live",
    "get_next_match_info",
    "get_last_match_info",
    "normalize_logo_url"
]