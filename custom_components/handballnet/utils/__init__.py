from .datetime_handler import DateTimeHandler
from .match_handler import MatchHandler
from .url_handler import URLHandler

class HandballNetUtils:
    """Zentrale Utilities-Klasse für handball.net Integration"""

    def __init__(self):
        self.datetime = DateTimeHandler()
        self.matches = MatchHandler()
        self.urls = URLHandler()

    # Direct access methods - so bleiben alle bestehenden Aufrufe funktional
    def normalize_logo_url(self, logo_url: str) -> str:
        """Direct access to normalize_logo_url"""
        return self.urls.normalize_logo_url(logo_url)

    def timestamp_to_datetime(self, timestamp: int):
        """Direct access to timestamp_to_datetime"""
        return self.datetime.timestamp_to_datetime(timestamp)

    def format_datetime_for_display(self, dt_or_timestamp):
        """Direct access to format_datetime_for_display"""
        return self.datetime.format_for_display(dt_or_timestamp)

    def is_game_live(self, start_timestamp: int, now=None):
        """Direct access to is_game_live"""
        return self.datetime.is_game_live(start_timestamp, now)

    def get_next_match_info(self, matches: list, now=None):
        """Direct access to get_next_match_info"""
        return self.matches.get_next_match(matches, now)

    def get_last_match_info(self, matches: list, now=None):
        """Direct access to get_last_match_info"""
        return self.matches.get_last_match(matches, now)

# Backward compatibility - standalone functions bleiben verfügbar
def timestamp_to_datetime(timestamp: int):
    return HandballNetUtils().timestamp_to_datetime(timestamp)

def format_datetime_for_display(dt_or_timestamp):
    return HandballNetUtils().format_datetime_for_display(dt_or_timestamp)

def is_game_live(start_timestamp: int, now=None):
    return HandballNetUtils().is_game_live(start_timestamp, now)

def get_next_match_info(matches: list, now=None):
    return HandballNetUtils().get_next_match_info(matches, now)

def get_last_match_info(matches: list, now=None):
    return HandballNetUtils().get_last_match_info(matches, now)

def normalize_logo_url(logo_url: str):
    return HandballNetUtils().normalize_logo_url(logo_url)

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