import asyncio
from types import SimpleNamespace

from custom_components.handballnet.config_flow import (  # noqa: E402
    CONF_SELECTED_TEAM_ID,
    HandballNetConfigFlow,
)


def test_reconfigure_select_team_filters_stale_default_ids():
    flow = HandballNetConfigFlow()
    flow._team_options = {
        "team-current-1": "Current Team 1",
        "team-current-2": "Current Team 2",
    }

    entry = SimpleNamespace(
        data={
            "team_mapping": {
                "Old Team": "team-stale",
                "Current Team 1": "team-current-1",
            }
        }
    )

    result = asyncio.run(flow.async_step_reconfigure_select_team(entry))

    assert result["step_id"] == "reconfigure_select_team"
    defaults = result["data_schema"]({})
    assert defaults[CONF_SELECTED_TEAM_ID] == ["team-current-1"]