from __future__ import annotations

from types import ModuleType
import sys


def _install_homeassistant_stubs() -> None:
    try:
        import homeassistant  # noqa: F401
        return
    except Exception:
        pass

    homeassistant = ModuleType("homeassistant")
    homeassistant.__path__ = []

    config_entries = ModuleType("homeassistant.config_entries")
    helpers = ModuleType("homeassistant.helpers")
    helpers.__path__ = []
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

        def async_create_entry(self, *, title, data):
            return {
                "type": "create_entry",
                "title": title,
                "data": data,
            }

        def async_abort(self, *, reason):
            return {"type": "abort", "reason": reason}

        def _async_current_entries(self):
            return []

    class OptionsFlow:
        def __init__(self):
            self.config_entry = None

        def async_create_entry(self, *, title, data):
            return {
                "type": "create_entry",
                "title": title,
                "data": data,
            }

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

    def callback(func):
        return func

    config_entries.ConfigFlow = ConfigFlow
    config_entries.OptionsFlow = OptionsFlow
    config_entries.ConfigEntry = ConfigEntry

    config_validation.multi_select = lambda options: (lambda value: value)
    config_validation.config_entry_only_config_schema = lambda domain: domain

    aiohttp_client.async_get_clientsession = lambda hass: None

    core.HomeAssistant = HomeAssistant
    core.callback = callback

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
