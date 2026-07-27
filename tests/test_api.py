import pytest
from unittest.mock import patch, AsyncMock

from .api_test_helpers import mocked_handball_api

@pytest.fixture
def api():
    with mocked_handball_api() as api_client:
        yield api_client

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


@pytest.mark.asyncio
async def test_get_tournament_team_ids_filters_by_default_tournament(api):
    api._make_request = AsyncMock(
        return_value={
            "data": [
                {
                    "id": "team-a",
                    "defaultTournament": {"id": "sr.competition.57"},
                },
                {
                    "id": "team-b",
                    "defaultTournament": {"id": "sr.competition.57"},
                },
                {
                    "id": "team-c",
                    "defaultTournament": {"id": "sr.competition.123"},
                },
                {
                    "id": "team-a",
                    "defaultTournament": {"id": "sr.competition.57"},
                },
                {
                    "id": "team-d",
                    "defaultTournament": None,
                },
            ]
        }
    )

    result = await api.get_tournament_team_ids("sr.competition.57")

    assert result == ["team-a", "team-b"]
    api._make_request.assert_called_once()


@pytest.mark.asyncio
async def test_get_tournament_team_ids_reads_all_pages(api):
    api._make_request = AsyncMock(
        side_effect=[
            {
                "data": [
                    {
                        "id": "team-a",
                        "defaultTournament": {"id": "sr.competition.57"},
                    }
                ],
                "meta": {"pageCount": 2},
            },
            {
                "data": [
                    {
                        "id": "team-b",
                        "defaultTournament": {"id": "sr.competition.57"},
                    },
                    {
                        "id": "team-c",
                        "defaultTournament": {"id": "sr.competition.999"},
                    },
                ],
                "meta": {"pageCount": 2},
            },
        ]
    )

    result = await api.get_tournament_team_ids("sr.competition.57")

    assert result == ["team-a", "team-b"]
    assert api._make_request.await_args_list[0].args[0].endswith("page=1")
    assert api._make_request.await_args_list[1].args[0].endswith("page=2")
