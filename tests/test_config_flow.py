import asyncio
from types import ModuleType, SimpleNamespace
import sys


def _install_homeassistant_stubs() -> None:
    if "homeassistant" in sys.modules:
        return

    homeassistant = ModuleType("homeassistant")
    config_entries = ModuleType("homeassistant.config_entries")
    helpers = ModuleType("homeassistant.helpers")
    config_validation = ModuleType("homeassistant.helpers.config_validation")
    aiohttp_client = ModuleType("homeassistant.helpers.aiohttp_client")
    core = ModuleType("homeassistant.core")

    class ConfigFlow:
        def __init_subclass__(cls, **kwargs):
            return None

        def async_show_form(self, *, step_id, data_schema, errors):
            return {
                "type": "form",
                "step_id": step_id,
                "data_schema": data_schema,
                "errors": errors,
            }

    class ConfigEntry:
        pass

    class HomeAssistant:
        pass

    config_entries.ConfigFlow = ConfigFlow
    config_entries.ConfigEntry = ConfigEntry
    config_validation.multi_select = lambda options: (lambda value: value)
    config_validation.config_entry_only_config_schema = lambda domain: domain
    aiohttp_client.async_get_clientsession = lambda hass: None
    core.HomeAssistant = HomeAssistant

    homeassistant.config_entries = config_entries
    homeassistant.helpers = helpers
    homeassistant.core = core
    helpers.config_validation = config_validation
    helpers.aiohttp_client = aiohttp_client

    sys.modules["homeassistant"] = homeassistant
    sys.modules["homeassistant.config_entries"] = config_entries
    sys.modules["homeassistant.helpers"] = helpers
    sys.modules["homeassistant.helpers.config_validation"] = config_validation
    sys.modules["homeassistant.helpers.aiohttp_client"] = aiohttp_client
    sys.modules["homeassistant.core"] = core


_install_homeassistant_stubs()

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