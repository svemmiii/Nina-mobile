"""Config flow for NINA Mobile."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)

from .const import (
    CONF_MESSAGE_SLOTS,
    CONF_TRACKER,
    DEFAULT_MESSAGE_SLOTS,
    DOMAIN,
    MAX_MESSAGE_SLOTS,
    MIN_MESSAGE_SLOTS,
)


class NinaMobileConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the NINA Mobile config flow."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure a GPS tracker and the number of stable warning slots."""
        errors: dict[str, str] = {}

        if user_input is not None:
            tracker = str(user_input[CONF_TRACKER])
            state = self.hass.states.get(tracker)

            if state is None:
                errors["base"] = "tracker_not_found"
            elif "latitude" not in state.attributes or "longitude" not in state.attributes:
                errors["base"] = "tracker_without_gps"
            else:
                await self.async_set_unique_id(tracker)
                self._abort_if_unique_id_configured()

                slots = int(user_input[CONF_MESSAGE_SLOTS])
                friendly_name = state.name or tracker
                return self.async_create_entry(
                    title=f"NINA Mobile – {friendly_name}",
                    data={
                        CONF_TRACKER: tracker,
                        CONF_MESSAGE_SLOTS: slots,
                    },
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_TRACKER): EntitySelector(
                    EntitySelectorConfig(domain="device_tracker")
                ),
                vol.Required(
                    CONF_MESSAGE_SLOTS,
                    default=DEFAULT_MESSAGE_SLOTS,
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=MIN_MESSAGE_SLOTS,
                        max=MAX_MESSAGE_SLOTS,
                        step=1,
                        mode=NumberSelectorMode.BOX,
                    )
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
