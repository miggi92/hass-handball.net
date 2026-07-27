import pytest
from unittest.mock import AsyncMock, patch

from .api_test_helpers import mocked_handball_api


@pytest.fixture
def api():
    with mocked_handball_api() as api_client:
        yield api_client


@pytest.mark.asyncio
async def test_team_schedule_caching(api):
    # Setup mock for _make_request
    api._make_request = AsyncMock(return_value={"data": [{"id": "match1"}]})

    # First call - should trigger request
    with patch("time.time", return_value=1000):
        result1 = await api.get_team_schedule("team123")

    assert result1 == [{"id": "match1"}]
    assert api._make_request.call_count == 1

    # Second call - within TTL - should NOT trigger request
    with patch("time.time", return_value=1000 + 1800):  # +30 mins
        result2 = await api.get_team_schedule("team123")

    assert result2 == [{"id": "match1"}]
    assert api._make_request.call_count == 1

    # Third call - after TTL - SHOULD trigger request
    with patch("time.time", return_value=1000 + 3601):  # +1 hour 1 sec
        result3 = await api.get_team_schedule("team123")

    assert result3 == [{"id": "match1"}]
    assert api._make_request.call_count == 2


@pytest.mark.asyncio
async def test_team_schedule_cache_limit(api):
    # Setup mock for _make_request
    api._make_request = AsyncMock(return_value={"data": []})

    # Fill cache with 20 items
    for i in range(20):
        await api.get_team_schedule(f"team{i}")

    assert len(api._team_schedule_cache) == 20
    assert api._make_request.call_count == 20

    # 21st item should clear cache and then add itself
    await api.get_team_schedule("team20")
    assert len(api._team_schedule_cache) == 1
    assert api._make_request.call_count == 21
    assert "team20" in api._team_schedule_cache


@pytest.mark.asyncio
async def test_team_schedule_no_cache_on_error(api):
    # Setup mock to return None (error)
    api._make_request = AsyncMock(return_value=None)

    result = await api.get_team_schedule("team123")
    assert result is None
    assert len(api._team_schedule_cache) == 0

    # If we call again, it should try again
    api._make_request.reset_mock()
    api._make_request.return_value = {"data": [{"id": "match2"}]}

    result = await api.get_team_schedule("team123")
    assert result == [{"id": "match2"}]
    assert api._make_request.call_count == 1
    assert len(api._team_schedule_cache) == 1
