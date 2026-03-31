import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import time
import sys
import os

# Add the root directory to sys.path to allow importing from custom_components
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Mock sys.modules for homeassistant dependencies
if "homeassistant" not in sys.modules:
    sys.modules["homeassistant"] = MagicMock()
    sys.modules["homeassistant.helpers"] = MagicMock()
    sys.modules["homeassistant.helpers.aiohttp_client"] = MagicMock()
    sys.modules["homeassistant.core"] = MagicMock()
    sys.modules["homeassistant.config_entries"] = MagicMock()

from custom_components.handballnet.api import HandballNetAPI

class TestHandballNetAPIPerformance(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.hass = MagicMock()
        with patch("custom_components.handballnet.api.HandballNetUtils", MagicMock()), \
             patch("custom_components.handballnet.api.async_get_clientsession", MagicMock()):
            self.api = HandballNetAPI(self.hass)

    async def test_team_schedule_caching(self):
        # Setup mock for _make_request
        self.api._make_request = AsyncMock(return_value={"data": [{"id": "match1"}]})

        # First call - should trigger request
        with patch("time.time", return_value=1000):
            result1 = await self.api.get_team_schedule("team123")

        self.assertEqual(result1, [{"id": "match1"}])
        self.assertEqual(self.api._make_request.call_count, 1)

        # Second call - within TTL - should NOT trigger request
        with patch("time.time", return_value=1000 + 1800): # +30 mins
            result2 = await self.api.get_team_schedule("team123")

        self.assertEqual(result2, [{"id": "match1"}])
        self.assertEqual(self.api._make_request.call_count, 1)

        # Third call - after TTL - SHOULD trigger request
        with patch("time.time", return_value=1000 + 3601): # +1 hour 1 sec
            result3 = await self.api.get_team_schedule("team123")

        self.assertEqual(result3, [{"id": "match1"}])
        self.assertEqual(self.api._make_request.call_count, 2)

    async def test_team_schedule_cache_limit(self):
        # Setup mock for _make_request
        self.api._make_request = AsyncMock(return_value={"data": []})

        # Fill cache with 20 items
        for i in range(20):
            await self.api.get_team_schedule(f"team{i}")

        self.assertEqual(len(self.api._team_schedule_cache), 20)
        self.assertEqual(self.api._make_request.call_count, 20)

        # 21st item should clear cache and then add itself
        await self.api.get_team_schedule("team20")
        self.assertEqual(len(self.api._team_schedule_cache), 1)
        self.assertEqual(self.api._make_request.call_count, 21)
        self.assertIn("team20", self.api._team_schedule_cache)

    async def test_team_schedule_no_cache_on_error(self):
        # Setup mock to return None (error)
        self.api._make_request = AsyncMock(return_value=None)

        result = await self.api.get_team_schedule("team123")
        self.assertIsNone(result)
        self.assertEqual(len(self.api._team_schedule_cache), 0)

        # If we call again, it should try again
        self.api._make_request.reset_mock()
        self.api._make_request.return_value = {"data": [{"id": "match2"}]}

        result = await self.api.get_team_schedule("team123")
        self.assertEqual(result, [{"id": "match2"}])
        self.assertEqual(self.api._make_request.call_count, 1)
        self.assertEqual(len(self.api._team_schedule_cache), 1)

if __name__ == "__main__":
    unittest.main()
