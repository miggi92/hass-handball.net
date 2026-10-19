"""Diagnostics support for handball.net.

Settings -> Devices & services -> handball.net -> "Download diagnostics"
produces a JSON file that can be attached to GitHub issues.
"""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import http_client
from .const import HANDBALL_NET_NEW_API_BASE_URL, HANDBALL_NET_WEB_URL

_MATCH_SAMPLE = 5


def _summarize_team(bucket: dict[str, Any]) -> dict[str, Any]:
    matches = bucket.get("matches") or []
    return {
        "team_id": bucket.get("team_id"),
        "team_name": bucket.get("team_name"),
        "tournament_id": bucket.get("tournament_id"),
        "table_position": bucket.get("table_position"),
        "health": bucket.get("health"),
        "is_live": bucket.get("is_live"),
        "match_count": len(matches),
        "home_matches": sum(1 for m in matches if m.get("isHomeMatch")),
        "away_matches": sum(1 for m in matches if m.get("isAway")),
        "next_match": bucket.get("next_match"),
        "last_match": bucket.get("last_match"),
        # Only a few raw matches: enough to debug parsing, small enough to read.
        "first_matches": matches[:_MATCH_SAMPLE],
        "last_matches": matches[-_MATCH_SAMPLE:],
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry (contains no credentials)."""
    coordinator = getattr(entry, "runtime_data", None)
    data = (getattr(coordinator, "data", None) or {}) if coordinator else {}
    teams = data.get("teams") or {}

    return {
        "entry": {
            "title": entry.title,
            "version": entry.version,
            "data": dict(entry.data),
            "options": dict(entry.options),
        },
        "api": {
            "base_url": HANDBALL_NET_NEW_API_BASE_URL,
            "referer_base": HANDBALL_NET_WEB_URL,
            "endpoints_currently_failing": dict(http_client._failures),
        },
        "coordinator": {
            "last_update_success": getattr(coordinator, "last_update_success", None),
            "update_interval": str(getattr(coordinator, "update_interval", None)),
            "last_exception": repr(getattr(coordinator, "last_exception", None)),
        },
        "teams": {team_id: _summarize_team(b) for team_id, b in teams.items()},
    }
