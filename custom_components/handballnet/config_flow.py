import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN, CONF_TEAM_ID

class HandballNetConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            team_id = user_input.get(CONF_TEAM_ID)
            if not team_id:
                errors[CONF_TEAM_ID] = "invalid_team_id"
            else:
                return self.async_create_entry(title=f"Team {team_id}", data=user_input)

        data_schema = vol.Schema({
            vol.Required(CONF_TEAM_ID): str,
        })

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )
