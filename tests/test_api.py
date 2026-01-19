import pytest
from unittest.mock import MagicMock, patch, AsyncMock
import time

# Mock sys.modules for homeassistant dependencies if they are not available
import sys
if "homeassistant" not in sys.modules:
    sys.modules["homeassistant"] = MagicMock()
    sys.modules["homeassistant.helpers"] = MagicMock()
    sys.modules["homeassistant.helpers.aiohttp_client"] = MagicMock()
    sys.modules["homeassistant.core"] = MagicMock()
    sys.modules["homeassistant.config_entries"] = MagicMock()

from custom_components.handballnet.api import HandballNetAPI

@pytest.fixture
def api():
    hass = MagicMock()
    # We need to mock session since it's used in __init__

    with patch("custom_components.handballnet.api.HandballNetUtils", MagicMock()), \
         patch("custom_components.handballnet.api.async_get_clientsession", MagicMock()):
        api = HandballNetAPI(hass)
        return api

@pytest.mark.asyncio
async def test_league_table_caching(api):
    # Setup mock for _make_request
    api._make_request = AsyncMock(return_value={"data": [{"rank": 1}]})

    # First call - should trigger request
    with patch("time.time", return_value=1000):
        result1 = await api.get_league_table("123")

    assert result1 == [{"rank": 1}]
    assert api._make_request.call_count == 1

    # Second call - within TTL - should NOT trigger request
    with patch("time.time", return_value=1000 + 1800): # +30 mins
        result2 = await api.get_league_table("123")

    assert result2 == [{"rank": 1}]
    assert api._make_request.call_count == 1

    # Third call - after TTL - SHOULD trigger request
    with patch("time.time", return_value=1000 + 3601): # +1 hour 1 sec
        result3 = await api.get_league_table("123")

    assert result3 == [{"rank": 1}]
    assert api._make_request.call_count == 2

@pytest.mark.asyncio
async def test_league_table_no_cache_on_error(api):
    # Setup mock to return None (error)
    api._make_request = AsyncMock(return_value=None)

    result = await api.get_league_table("123")
    assert result is None

    # If we call again, it should try again (no cache for None)
    api._make_request.reset_mock()
    api._make_request.return_value = {"data": [{"rank": 2}]}

    result = await api.get_league_table("123")
    assert result == [{"rank": 2}]
    assert api._make_request.call_count == 1
