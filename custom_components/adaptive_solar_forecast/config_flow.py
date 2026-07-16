"""Config flow for Adaptive Solar Forecast."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import (
    CONF_ACTUAL_PRODUCTION_ENTITY,
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
    CONF_BATTERY_FULL_ENTITY,
    CONF_BATTERY_FULL_THRESHOLD,
    CONF_BATTERY_POWER_ENTITY,
    CONF_CALIBRATION_CLIP_WATTS,
    CONF_CALIBRATION_DAYS,
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
    DEFAULT_BATTERY_FULL_THRESHOLD,
    DEFAULT_CALIBRATION_CLIP_WATTS,
    DEFAULT_CALIBRATION_DAYS,
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
            vol.Optional(
                CONF_ACTUAL_PRODUCTION_ENTITY,
                default=defaults.get(CONF_ACTUAL_PRODUCTION_ENTITY),
            ): _entity_selector("sensor"),
            vol.Optional(
                CONF_BATTERY_FULL_ENTITY,
                default=defaults.get(CONF_BATTERY_FULL_ENTITY),
            ): _entity_selector("sensor"),
            vol.Optional(
                CONF_BATTERY_FULL_THRESHOLD,
                default=defaults.get(CONF_BATTERY_FULL_THRESHOLD, DEFAULT_BATTERY_FULL_THRESHOLD),
            ): _number_selector(min_value=0, max_value=100, step=1),
            vol.Optional(
                CONF_BATTERY_POWER_ENTITY,
                default=defaults.get(CONF_BATTERY_POWER_ENTITY),
            ): _entity_selector("sensor"),
            vol.Optional(
                CONF_CALIBRATION_CLIP_WATTS,
                default=defaults.get(CONF_CALIBRATION_CLIP_WATTS, DEFAULT_CALIBRATION_CLIP_WATTS),
            ): _number_selector(min_value=0, max_value=20000, step=10),
            vol.Optional(
                CONF_CALIBRATION_DAYS,
                default=defaults.get(CONF_CALIBRATION_DAYS, DEFAULT_CALIBRATION_DAYS),
            ): _number_selector(min_value=1, max_value=90, step=1),
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


def _validate_threshold_ordering(data: Mapping[str, Any]) -> dict[str, str]:
    """Validate ordering constraints for azimuth/elevation thresholds."""
    errors: dict[str, str] = {}

    def _get_float(key: str) -> float | None:
        value = data.get(key)
        if value is None:
            return None
        return float(value)

    morning_keys = (
        CONF_MORNING_FREE_AZIMUTH,
        CONF_MORNING_SHADE_START_AZIMUTH,
        CONF_MORNING_SHADE_END_AZIMUTH,
        CONF_MORNING_RECOVER_AZIMUTH,
    )
    morning_values = [_get_float(key) for key in morning_keys]
    if all(value is not None for value in morning_values):
        free, shade_start, shade_end, recover = morning_values
        if not (free <= shade_start <= shade_end <= recover):
            for key in morning_keys:
                errors[key] = "morning_azimuth_order"

    afternoon_keys = (
        CONF_AFTERNOON_HIGH_ELEVATION,
        CONF_AFTERNOON_MID_ELEVATION,
        CONF_AFTERNOON_LOW_ELEVATION,
        CONF_AFTERNOON_DEEP_ELEVATION,
        CONF_AFTERNOON_END_ELEVATION,
    )
    afternoon_values = [_get_float(key) for key in afternoon_keys]
    if all(value is not None for value in afternoon_values):
        high, mid, low, deep, end = afternoon_values
        if not (high >= mid >= low >= deep >= end):
            for key in afternoon_keys:
                errors[key] = "afternoon_elevation_order"

    return errors


class AdaptiveSolarForecastConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Adaptive Solar Forecast."""

    VERSION = 1
    _base_input: dict[str, Any]

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "AdaptiveSolarForecastOptionsFlow":
        """Create the options flow."""
        return AdaptiveSolarForecastOptionsFlow()

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
            errors = _validate_threshold_ordering(data)
            if errors:
                return self.async_show_form(
                    step_id="advanced",
                    data_schema=_advanced_schema(user_input),
                    errors=errors,
                )
            await self.async_set_unique_id(data[CONF_NAME].lower().replace(" ", "_"))
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=data[CONF_NAME], data=data)

        return self.async_show_form(step_id="advanced", data_schema=_advanced_schema({}))


class AdaptiveSolarForecastOptionsFlow(config_entries.OptionsFlow):
    """Handle options for Adaptive Solar Forecast."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Manage the options."""
        if user_input is not None:
            errors = _validate_threshold_ordering(user_input)
            if errors:
                return self.async_show_form(
                    step_id="init",
                    data_schema=vol.Schema(
                        {
                            **_base_schema(user_input).schema,
                            **_advanced_schema(user_input).schema,
                        }
                    ),
                    errors=errors,
                )
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
