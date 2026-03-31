import unittest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os
import time
from typing import Any

# Mock homeassistant
class MockPackage(MagicMock):
    @property
    def __path__(self):
        return []

ha = MockPackage()
sys.modules["homeassistant"] = ha
sys.modules["homeassistant.helpers"] = MockPackage()
sys.modules["homeassistant.helpers.aiohttp_client"] = MagicMock()
sys.modules["homeassistant.core"] = MagicMock()
sys.modules["homeassistant.config_entries"] = MagicMock()

# Add the current directory to sys.path
sys.path.append(os.getcwd())

from custom_components.handballnet.api import HandballNetAPI

class TestHandballNetAPITeamCache(unittest.IsolatedAsyncioTestCase):
    """Test team info caching in HandballNetAPI."""

    def setUp(self) -> None:
        """Set up the test environment."""
        self.hass = MagicMock()
        with patch("custom_components.handballnet.api.HandballNetUtils", MagicMock()), \
             patch("custom_components.handballnet.api.async_get_clientsession", MagicMock()):
            self.api = HandballNetAPI(self.hass)

    async def test_team_info_caching(self) -> None:
        """Test that team info is correctly cached."""
        # Setup mock for _make_request
        self.api._make_request = AsyncMock(return_value={"data": {"id": "team1", "name": "Team 1"}})

        # First call - should trigger request
        with patch("time.time", return_value=1000):
            result1 = await self.api.get_team_info("team1")

        assert result1 == {"id": "team1", "name": "Team 1"}
        assert self.api._make_request.call_count == 1

        # Second call - within TTL - should NOT trigger request
        with patch("time.time", return_value=1000 + 3600): # +1 hour
            result2 = await self.api.get_team_info("team1")

        assert result2 == {"id": "team1", "name": "Team 1"}
        assert self.api._make_request.call_count == 1

        # Third call - after TTL - SHOULD trigger request
        # TTL is 86400 (24 hours)
        with patch("time.time", return_value=1000 + 86401): # +24 hours 1 sec
            result3 = await self.api.get_team_info("team1")

        assert result3 == {"id": "team1", "name": "Team 1"}
        assert self.api._make_request.call_count == 2

    async def test_team_info_no_cache_on_error(self) -> None:
        """Test that errors are not cached."""
        # Setup mock to return None (error)
        self.api._make_request = AsyncMock(return_value=None)

        result = await self.api.get_team_info("team1")
        assert result is None

        # If we call again, it should try again (no cache for None)
        self.api._make_request.reset_mock()
        self.api._make_request.return_value = {"data": {"id": "team1", "name": "Team 1"}}

        result = await self.api.get_team_info("team1")
        assert result == {"id": "team1", "name": "Team 1"}
        assert self.api._make_request.call_count == 1

    async def test_team_info_cache_unbounded_growth_prevention(self) -> None:
        """Test that the cache does not grow indefinitely."""
        # Mock _make_request to return unique data for each team
        async def mock_request(endpoint: str) -> dict[str, Any]:
            team_id = endpoint.split("/")[-1]
            return {"data": {"id": team_id}}

        self.api._make_request = AsyncMock(side_effect=mock_request)

        # Fill the cache up to the limit (50)
        for i in range(50):
            await self.api.get_team_info(f"team{i}")

        assert len(self.api._team_info_cache) == 50

        # Adding one more should clear and add the new one
        await self.api.get_team_info("team50")
        assert len(self.api._team_info_cache) == 1
        assert "team50" in self.api._team_info_cache

if __name__ == "__main__":
    unittest.main()
