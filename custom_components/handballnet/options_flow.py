import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL, CONF_UPDATE_INTERVAL_LIVE, DEFAULT_UPDATE_INTERVAL_LIVE

class HandballNetOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        """Initialize the options flow."""
        # The parent class constructor handles this properly
        super().__init__()

    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_UPDATE_INTERVAL,
                        self.config_entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
                    )
                ): int,
                vol.Optional(
                    CONF_UPDATE_INTERVAL_LIVE,
                    default=self.config_entry.options.get(
                        CONF_UPDATE_INTERVAL_LIVE,
                        self.config_entry.data.get(CONF_UPDATE_INTERVAL_LIVE, DEFAULT_UPDATE_INTERVAL_LIVE)
                    )
                ): int,
            }),
            errors=errors
        )


@callback
def async_get_options_flow(config_entry):
    return HandballNetOptionsFlowHandler(config_entry)