import voluptuous as vol
from homeassistant import config_entries
from .const import (
    DOMAIN,
    CONF_TEAM_ID,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    CONF_UPDATE_INTERVAL_LIVE,
    DEFAULT_UPDATE_INTERVAL_LIVE
)

class HandballNetConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry):
        from .options_flow import HandballNetOptionsFlowHandler
        return HandballNetOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            team_id = user_input.get(CONF_TEAM_ID)

            if not team_id:
                errors[CONF_TEAM_ID] = "invalid_team_id"
            else:
                for entry in self._async_current_entries():
                    if entry.data[CONF_TEAM_ID] == team_id:
                        errors[CONF_TEAM_ID] = "already_configured"
                        break

                if not errors:
                    return self.async_create_entry(title=f"Team {team_id}", data=user_input)

        data_schema = vol.Schema({
            vol.Required(CONF_TEAM_ID): str,
            vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): int,
            vol.Optional(CONF_UPDATE_INTERVAL_LIVE, default=DEFAULT_UPDATE_INTERVAL_LIVE): int
        })

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )
