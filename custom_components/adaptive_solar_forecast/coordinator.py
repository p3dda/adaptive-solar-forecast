"""Coordinator for Adaptive Solar Forecast."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from typing import Any

from astral import Observer

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_FORECAST_TODAY_ENTITY,
    CONF_FORECAST_TOMORROW_ENTITY,
    CONF_NAME,
    CONF_SUN_ENTITY,
    CONF_UPDATE_INTERVAL,
)
from .model import ModelConfig, adjust_forecast_dataset, calculate_current_factor, model_config_from_mapping

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class ForecastDataset:
    """Normalized forecast data from a forecast entity."""

    entity_id: str
    watts: dict[datetime, float]
    watt_hours: dict[datetime, float]
    native_state: float | None


class AdaptiveSolarForecastCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch and compute adaptive solar forecast data."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.config_entry = config_entry
        merged = {**config_entry.data, **config_entry.options}
        self._config = merged
        self._model = model_config_from_mapping(merged)

        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=merged[CONF_NAME],
            update_interval=timedelta(minutes=int(merged[CONF_UPDATE_INTERVAL])),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Home Assistant and build adjusted forecast outputs."""
        today_dataset = self._build_dataset(self._config[CONF_FORECAST_TODAY_ENTITY])
        tomorrow_entity = self._config.get(CONF_FORECAST_TOMORROW_ENTITY)
        tomorrow_dataset = self._build_dataset(tomorrow_entity) if tomorrow_entity else None

        observer = self._build_observer()

        sun_state = self.hass.states.get(self._config[CONF_SUN_ENTITY])
        if sun_state is None:
            raise UpdateFailed(f"Sun entity {self._config[CONF_SUN_ENTITY]} not found")

        try:
            current_azimuth = float(sun_state.attributes.get("azimuth"))
            current_elevation = float(sun_state.attributes.get("elevation"))
        except (KeyError, TypeError, ValueError) as err:
            available = self._format_attribute_keys(sun_state.attributes)
            raise UpdateFailed(
                "Sun entity is missing or has invalid azimuth/elevation attributes. "
                f"Available attributes: {available}"
            ) from err

        today_adjusted = adjust_forecast_dataset(observer, today_dataset, self._model)
        tomorrow_adjusted = adjust_forecast_dataset(observer, tomorrow_dataset, self._model) if tomorrow_dataset else None

        return {
            "config": self._config,
            "model": self._model,
            "today": today_adjusted,
            "tomorrow": tomorrow_adjusted,
            "current_factor": calculate_current_factor(
                azimuth=current_azimuth,
                elevation=current_elevation,
                config=self._model,
            ),
            "current_azimuth": current_azimuth,
            "current_elevation": current_elevation,
        }

    def _build_observer(self) -> Observer:
        """Build an Astral observer from Home Assistant's configured location."""
        return Observer(
            latitude=self.hass.config.latitude,
            longitude=self.hass.config.longitude,
            elevation=self.hass.config.elevation,
        )

    def _build_dataset(self, entity_id: str | None) -> ForecastDataset | None:
        """Normalize a forecast entity into structured data."""
        if not entity_id:
            return None

        state = self.hass.states.get(entity_id)
        if state is None:
            raise UpdateFailed(f"Forecast entity {entity_id} not found")

        raw_watts = state.attributes.get("watts")
        raw_watt_hours = state.attributes.get("wh_period")
        watts = self._normalize_time_series(raw_watts)
        watt_hours = self._normalize_time_series(raw_watt_hours)

        if not watts and not watt_hours:
            available = self._format_attribute_keys(state.attributes)
            raise UpdateFailed(
                "Forecast entity "
                f"{entity_id} must expose either 'watts' or 'wh_period' as dicts "
                f"(got watts={type(raw_watts).__name__}, wh_period={type(raw_watt_hours).__name__}). "
                f"Available attributes: {available}"
            )

        try:
            native_state = float(state.state)
        except (TypeError, ValueError):
            native_state = None

        return ForecastDataset(
            entity_id=entity_id,
            watts=watts,
            watt_hours=watt_hours,
            native_state=native_state,
        )

    def _normalize_time_series(self, values: Any) -> dict[datetime, float]:
        """Convert forecast attributes to timezone-aware datetime maps."""
        if not isinstance(values, dict):
            return {}

        normalized: dict[datetime, float] = {}
        for raw_key, raw_value in values.items():
            try:
                dt = dt_util.parse_datetime(str(raw_key))
                value = float(raw_value)
            except (TypeError, ValueError):
                continue

            if dt is None:
                continue

            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=dt_util.UTC)

            normalized[dt] = value

        return dict(sorted(normalized.items()))

    @staticmethod
    def _format_attribute_keys(attributes: dict[str, Any], limit: int = 20) -> str:
        """Format attribute keys for error messages."""
        keys = sorted(attributes.keys())
        if len(keys) <= limit:
            return ", ".join(keys)
        return ", ".join(keys[:limit]) + f", ... (+{len(keys) - limit} more)"
