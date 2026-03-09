"""Config flow for Adaptive Solar Forecast."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import (
    CONF_AFTERNOON_DEEP_ELEVATION,
    CONF_AFTERNOON_DEEP_FACTOR,
    CONF_AFTERNOON_END_ELEVATION,
    CONF_AFTERNOON_END_FACTOR,
    CONF_AFTERNOON_HIGH_ELEVATION,
    CONF_AFTERNOON_HORIZON_FACTOR,
    CONF_AFTERNOON_LOW_ELEVATION,
    CONF_AFTERNOON_LOW_FACTOR,
    CONF_AFTERNOON_MID_ELEVATION,
    CONF_AFTERNOON_MID_FACTOR,
    CONF_AFTER_SOLAR_NOON_ONLY,
    CONF_FORECAST_TODAY_ENTITY,
    CONF_FORECAST_TOMORROW_ENTITY,
    CONF_MORNING_DEEP_FACTOR,
    CONF_MORNING_FREE_AZIMUTH,
    CONF_MORNING_RECOVER_AZIMUTH,
    CONF_MORNING_SHADE_END_AZIMUTH,
    CONF_MORNING_SHADE_START_AZIMUTH,
    CONF_NAME,
    CONF_SUN_ENTITY,
    CONF_UPDATE_INTERVAL,
    DEFAULT_AFTERNOON_DEEP_ELEVATION,
    DEFAULT_AFTERNOON_DEEP_FACTOR,
    DEFAULT_AFTERNOON_END_ELEVATION,
    DEFAULT_AFTERNOON_END_FACTOR,
    DEFAULT_AFTERNOON_HIGH_ELEVATION,
    DEFAULT_AFTERNOON_HORIZON_FACTOR,
    DEFAULT_AFTERNOON_LOW_ELEVATION,
    DEFAULT_AFTERNOON_LOW_FACTOR,
    DEFAULT_AFTERNOON_MID_ELEVATION,
    DEFAULT_AFTERNOON_MID_FACTOR,
    DEFAULT_AFTER_SOLAR_NOON_ONLY,
    DEFAULT_MORNING_DEEP_FACTOR,
    DEFAULT_MORNING_FREE_AZIMUTH,
    DEFAULT_MORNING_RECOVER_AZIMUTH,
    DEFAULT_MORNING_SHADE_END_AZIMUTH,
    DEFAULT_MORNING_SHADE_START_AZIMUTH,
    DEFAULT_NAME,
    DEFAULT_SUN_ENTITY,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)


def _entity_selector(domain: str | None = None) -> selector.EntitySelector:
    """Build an entity selector."""
    config = selector.EntitySelectorConfig(domain=domain) if domain else selector.EntitySelectorConfig()
    return selector.EntitySelector(config)


def _number_selector(
    *,
    min_value: float,
    max_value: float,
    step: float,
) -> selector.NumberSelector:
    """Build a number selector."""
    return selector.NumberSelector(
        selector.NumberSelectorConfig(min=min_value, max=max_value, step=step, mode=selector.NumberSelectorMode.BOX)
    )


def _base_schema(defaults: Mapping[str, Any]) -> vol.Schema:
    """Create the main config schema."""
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=defaults.get(CONF_NAME, DEFAULT_NAME)): selector.TextSelector(),
            vol.Required(
                CONF_FORECAST_TODAY_ENTITY,
                default=defaults.get(CONF_FORECAST_TODAY_ENTITY),
            ): _entity_selector("sensor"),
            vol.Optional(
                CONF_FORECAST_TOMORROW_ENTITY,
                default=defaults.get(CONF_FORECAST_TOMORROW_ENTITY),
            ): _entity_selector("sensor"),
            vol.Required(
                CONF_SUN_ENTITY,
                default=defaults.get(CONF_SUN_ENTITY, DEFAULT_SUN_ENTITY),
            ): _entity_selector("sun"),
            vol.Required(
                CONF_UPDATE_INTERVAL,
                default=defaults.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
            ): _number_selector(min_value=5, max_value=120, step=5),
        }
    )


def _advanced_schema(defaults: Mapping[str, Any]) -> vol.Schema:
    """Create the advanced tuning schema."""
    return vol.Schema(
        {
            vol.Required(
                CONF_MORNING_FREE_AZIMUTH,
                default=defaults.get(CONF_MORNING_FREE_AZIMUTH, DEFAULT_MORNING_FREE_AZIMUTH),
            ): _number_selector(min_value=0, max_value=180, step=1),
            vol.Required(
                CONF_MORNING_SHADE_START_AZIMUTH,
                default=defaults.get(CONF_MORNING_SHADE_START_AZIMUTH, DEFAULT_MORNING_SHADE_START_AZIMUTH),
            ): _number_selector(min_value=0, max_value=180, step=1),
            vol.Required(
                CONF_MORNING_SHADE_END_AZIMUTH,
                default=defaults.get(CONF_MORNING_SHADE_END_AZIMUTH, DEFAULT_MORNING_SHADE_END_AZIMUTH),
            ): _number_selector(min_value=0, max_value=180, step=1),
            vol.Required(
                CONF_MORNING_RECOVER_AZIMUTH,
                default=defaults.get(CONF_MORNING_RECOVER_AZIMUTH, DEFAULT_MORNING_RECOVER_AZIMUTH),
            ): _number_selector(min_value=0, max_value=180, step=1),
            vol.Required(
                CONF_MORNING_DEEP_FACTOR,
                default=defaults.get(CONF_MORNING_DEEP_FACTOR, DEFAULT_MORNING_DEEP_FACTOR),
            ): _number_selector(min_value=0, max_value=1, step=0.01),
            vol.Required(
                CONF_AFTERNOON_HIGH_ELEVATION,
                default=defaults.get(CONF_AFTERNOON_HIGH_ELEVATION, DEFAULT_AFTERNOON_HIGH_ELEVATION),
            ): _number_selector(min_value=-10, max_value=90, step=1),
            vol.Required(
                CONF_AFTERNOON_MID_ELEVATION,
                default=defaults.get(CONF_AFTERNOON_MID_ELEVATION, DEFAULT_AFTERNOON_MID_ELEVATION),
            ): _number_selector(min_value=-10, max_value=90, step=1),
            vol.Required(
                CONF_AFTERNOON_LOW_ELEVATION,
                default=defaults.get(CONF_AFTERNOON_LOW_ELEVATION, DEFAULT_AFTERNOON_LOW_ELEVATION),
            ): _number_selector(min_value=-10, max_value=90, step=1),
            vol.Required(
                CONF_AFTERNOON_DEEP_ELEVATION,
                default=defaults.get(CONF_AFTERNOON_DEEP_ELEVATION, DEFAULT_AFTERNOON_DEEP_ELEVATION),
            ): _number_selector(min_value=-10, max_value=90, step=1),
            vol.Required(
                CONF_AFTERNOON_END_ELEVATION,
                default=defaults.get(CONF_AFTERNOON_END_ELEVATION, DEFAULT_AFTERNOON_END_ELEVATION),
            ): _number_selector(min_value=-10, max_value=90, step=1),
            vol.Required(
                CONF_AFTERNOON_MID_FACTOR,
                default=defaults.get(CONF_AFTERNOON_MID_FACTOR, DEFAULT_AFTERNOON_MID_FACTOR),
            ): _number_selector(min_value=0, max_value=1, step=0.01),
            vol.Required(
                CONF_AFTERNOON_LOW_FACTOR,
                default=defaults.get(CONF_AFTERNOON_LOW_FACTOR, DEFAULT_AFTERNOON_LOW_FACTOR),
            ): _number_selector(min_value=0, max_value=1, step=0.01),
            vol.Required(
                CONF_AFTERNOON_DEEP_FACTOR,
                default=defaults.get(CONF_AFTERNOON_DEEP_FACTOR, DEFAULT_AFTERNOON_DEEP_FACTOR),
            ): _number_selector(min_value=0, max_value=1, step=0.01),
            vol.Required(
                CONF_AFTERNOON_END_FACTOR,
                default=defaults.get(CONF_AFTERNOON_END_FACTOR, DEFAULT_AFTERNOON_END_FACTOR),
            ): _number_selector(min_value=0, max_value=1, step=0.01),
            vol.Required(
                CONF_AFTERNOON_HORIZON_FACTOR,
                default=defaults.get(CONF_AFTERNOON_HORIZON_FACTOR, DEFAULT_AFTERNOON_HORIZON_FACTOR),
            ): _number_selector(min_value=0, max_value=1, step=0.01),
            vol.Required(
                CONF_AFTER_SOLAR_NOON_ONLY,
                default=defaults.get(CONF_AFTER_SOLAR_NOON_ONLY, DEFAULT_AFTER_SOLAR_NOON_ONLY),
            ): selector.BooleanSelector(),
        }
    )


class AdaptiveSolarForecastConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Adaptive Solar Forecast."""

    VERSION = 1
    _base_input: dict[str, Any]

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "AdaptiveSolarForecastOptionsFlow":
        """Create the options flow."""
        return AdaptiveSolarForecastOptionsFlow(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Handle the initial step."""
        if user_input is not None:
            self._base_input = user_input
            return await self.async_step_advanced()

        return self.async_show_form(step_id="user", data_schema=_base_schema({}))

    async def async_step_advanced(self, user_input: dict[str, Any] | None = None):
        """Handle advanced shading tuning."""
        if user_input is not None:
            data = {**self._base_input, **user_input}
            await self.async_set_unique_id(data[CONF_NAME].lower().replace(" ", "_"))
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=data[CONF_NAME], data=data)

        return self.async_show_form(step_id="advanced", data_schema=_advanced_schema({}))


class AdaptiveSolarForecastOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Adaptive Solar Forecast."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        defaults = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    **_base_schema(defaults).schema,
                    **_advanced_schema(defaults).schema,
                }
            ),
        )
