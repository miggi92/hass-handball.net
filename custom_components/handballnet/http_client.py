"""Shared HTTP helper for the new handball.net API (/api/new).

Every failure is logged with enough context (endpoint, params, HTTP status,
Cloudflare ray id, response excerpt) to be pasted directly into a GitHub issue.
Repeated identical failures are logged only once at WARNING (then DEBUG) so the
log is not flooded by coordinator polling; recovery is logged at INFO.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import HANDBALL_NET_NEW_API_BASE_URL

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30)
_BODY_EXCERPT = 300

# endpoint -> signature of the last logged failure
_failures: dict[str, str] = {}

_STATUS_HINTS = {
    401: "authentication required",
    403: "request rejected by handball.net/Cloudflare - check that the Referer "
    "matches the API origin (https://handball.net/...)",
    404: "resource not found - team/club/competition id may be invalid or outdated",
    429: "rate limited by handball.net - reduce the update interval",
}


class HandballNetHTTPError(Exception):
    """Raised when handball.net cannot be reached or does not answer with usable JSON."""

    def __init__(self, status: int | None, endpoint: str, reason: str) -> None:
        super().__init__(f"{endpoint}: {reason}")
        self.status = status
        self.endpoint = endpoint
        self.reason = reason


def _excerpt(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= _BODY_EXCERPT else text[:_BODY_EXCERPT] + "..."


def _log_failure(endpoint: str, signature: str, message: str, *args: Any) -> None:
    if _failures.get(endpoint) == signature:
        _LOGGER.debug(message + " (repeated)", *args)
        return
    _failures[endpoint] = signature
    _LOGGER.warning(message, *args)


def _log_success(endpoint: str) -> None:
    if _failures.pop(endpoint, None) is not None:
        _LOGGER.info("handball.net API reachable again: %s", endpoint)


async def async_get_json(
    hass: HomeAssistant, endpoint: str, params: dict[str, Any], referer: str
) -> dict[str, Any]:
    """GET an /api/new endpoint and return the parsed JSON.

    handball.net (behind Cloudflare) rejects requests without a same-origin
    Referer (https://handball.net/...) with HTTP 403.

    Raises HandballNetHTTPError on network errors, non-200 status codes and
    non-JSON responses. A JSON body with "success": false is logged but still
    returned, so callers keep their existing handling.
    """
    session = async_get_clientsession(hass)
    url = f"{HANDBALL_NET_NEW_API_BASE_URL}/{endpoint}"

    try:
        async with session.get(
            url, params=params, headers={"Referer": referer}, timeout=REQUEST_TIMEOUT
        ) as resp:
            ray = resp.headers.get("cf-ray", "-")
            text = await resp.text()

            if resp.status != 200:
                hint = _STATUS_HINTS.get(resp.status, "unexpected status")
                _log_failure(
                    endpoint,
                    f"http-{resp.status}",
                    "handball.net API error: HTTP %s for %s (%s) | params=%s | "
                    "referer=%s | cf-ray=%s | response: %s",
                    resp.status,
                    endpoint,
                    hint,
                    params,
                    referer,
                    ray,
                    _excerpt(text),
                )
                raise HandballNetHTTPError(resp.status, endpoint, f"HTTP {resp.status}: {hint}")

            try:
                payload = await resp.json(content_type=None)
            except ValueError:
                _log_failure(
                    endpoint,
                    "no-json",
                    "handball.net API error: HTTP 200 but no valid JSON for %s "
                    "(content-type=%s, cf-ray=%s, possibly a Cloudflare challenge page) | "
                    "response: %s",
                    endpoint,
                    resp.headers.get("content-type"),
                    ray,
                    _excerpt(text),
                )
                raise HandballNetHTTPError(200, endpoint, "response is not JSON") from None

    except HandballNetHTTPError:
        raise
    except asyncio.TimeoutError:
        _log_failure(
            endpoint,
            "timeout",
            "handball.net API error: timeout after %ss for %s",
            REQUEST_TIMEOUT.total,
            endpoint,
        )
        raise HandballNetHTTPError(None, endpoint, "timeout") from None
    except aiohttp.ClientError as err:
        _log_failure(
            endpoint,
            f"client-{type(err).__name__}",
            "handball.net API error: connection problem for %s: %s: %s",
            endpoint,
            type(err).__name__,
            err,
        )
        raise HandballNetHTTPError(None, endpoint, str(err)) from err

    if isinstance(payload, dict) and payload.get("success") is False:
        detail = payload.get("error") or payload.get("message") or payload.get("errors")
        _log_failure(
            endpoint,
            f"success-false-{detail}",
            "handball.net API reported an error for %s | params=%s | error=%s | response: %s",
            endpoint,
            params,
            detail,
            _excerpt(str(payload)),
        )
        return payload

    _log_success(endpoint)
    return payload
