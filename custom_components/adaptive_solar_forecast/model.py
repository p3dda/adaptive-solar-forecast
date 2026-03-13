"""Forecast adjustment model for Adaptive Solar Forecast."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from statistics import mean
from typing import Any

from astral import Observer
from astral.sun import azimuth as solar_azimuth
from astral.sun import elevation as solar_elevation

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
    CONF_MORNING_DEEP_FACTOR,
    CONF_MORNING_FREE_AZIMUTH,
    CONF_MORNING_RECOVER_AZIMUTH,
    CONF_MORNING_SHADE_END_AZIMUTH,
    CONF_MORNING_SHADE_START_AZIMUTH,
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
)


@dataclass
class ModelConfig:
    """Piecewise shading model parameters."""

    morning_free_azimuth: float
    morning_shade_start_azimuth: float
    morning_shade_end_azimuth: float
    morning_recover_azimuth: float
    morning_deep_factor: float
    afternoon_high_elevation: float
    afternoon_mid_elevation: float
    afternoon_low_elevation: float
    afternoon_deep_elevation: float
    afternoon_end_elevation: float
    afternoon_mid_factor: float
    afternoon_low_factor: float
    afternoon_deep_factor: float
    afternoon_end_factor: float
    afternoon_horizon_factor: float
    after_solar_noon_only: bool


def model_config_from_mapping(data: dict[str, Any]) -> ModelConfig:
    """Build the model config from config entry data."""
    return ModelConfig(
        morning_free_azimuth=float(data.get(CONF_MORNING_FREE_AZIMUTH, DEFAULT_MORNING_FREE_AZIMUTH)),
        morning_shade_start_azimuth=float(
            data.get(CONF_MORNING_SHADE_START_AZIMUTH, DEFAULT_MORNING_SHADE_START_AZIMUTH)
        ),
        morning_shade_end_azimuth=float(
            data.get(CONF_MORNING_SHADE_END_AZIMUTH, DEFAULT_MORNING_SHADE_END_AZIMUTH)
        ),
        morning_recover_azimuth=float(data.get(CONF_MORNING_RECOVER_AZIMUTH, DEFAULT_MORNING_RECOVER_AZIMUTH)),
        morning_deep_factor=float(data.get(CONF_MORNING_DEEP_FACTOR, DEFAULT_MORNING_DEEP_FACTOR)),
        afternoon_high_elevation=float(
            data.get(CONF_AFTERNOON_HIGH_ELEVATION, DEFAULT_AFTERNOON_HIGH_ELEVATION)
        ),
        afternoon_mid_elevation=float(data.get(CONF_AFTERNOON_MID_ELEVATION, DEFAULT_AFTERNOON_MID_ELEVATION)),
        afternoon_low_elevation=float(data.get(CONF_AFTERNOON_LOW_ELEVATION, DEFAULT_AFTERNOON_LOW_ELEVATION)),
        afternoon_deep_elevation=float(
            data.get(CONF_AFTERNOON_DEEP_ELEVATION, DEFAULT_AFTERNOON_DEEP_ELEVATION)
        ),
        afternoon_end_elevation=float(data.get(CONF_AFTERNOON_END_ELEVATION, DEFAULT_AFTERNOON_END_ELEVATION)),
        afternoon_mid_factor=float(data.get(CONF_AFTERNOON_MID_FACTOR, DEFAULT_AFTERNOON_MID_FACTOR)),
        afternoon_low_factor=float(data.get(CONF_AFTERNOON_LOW_FACTOR, DEFAULT_AFTERNOON_LOW_FACTOR)),
        afternoon_deep_factor=float(data.get(CONF_AFTERNOON_DEEP_FACTOR, DEFAULT_AFTERNOON_DEEP_FACTOR)),
        afternoon_end_factor=float(data.get(CONF_AFTERNOON_END_FACTOR, DEFAULT_AFTERNOON_END_FACTOR)),
        afternoon_horizon_factor=float(
            data.get(CONF_AFTERNOON_HORIZON_FACTOR, DEFAULT_AFTERNOON_HORIZON_FACTOR)
        ),
        after_solar_noon_only=bool(data.get(CONF_AFTER_SOLAR_NOON_ONLY, DEFAULT_AFTER_SOLAR_NOON_ONLY)),
    )


def calculate_current_factor(*, azimuth: float, elevation: float, config: ModelConfig) -> float:
    """Calculate the current combined shading factor."""
    return min(_morning_factor(azimuth, config), _afternoon_factor(azimuth, elevation, config))


def adjust_forecast_dataset(
    observer: Observer,
    dataset: Any,
    config: ModelConfig,
) -> dict[str, Any] | None:
    """Apply the shading model to a normalized forecast dataset."""
    if dataset is None:
        return None

    adjusted_watts: dict[str, float] = {}
    adjusted_watt_hours: dict[str, float] = {}
    factors: list[float] = []

    for timestamp, watts in dataset.watts.items():
        factor = _factor_for_timestamp(observer, timestamp, config)
        adjusted_watts[timestamp.isoformat()] = round(watts * factor, 3)
        factors.append(factor)

    if dataset.watt_hours:
        for timestamp, watt_hours in dataset.watt_hours.items():
            factor = _factor_for_timestamp(observer, timestamp, config)
            adjusted_watt_hours[timestamp.isoformat()] = round(watt_hours * factor, 3)
            factors.append(factor)
    else:
        adjusted_watt_hours = _derive_watt_hours_from_watts(adjusted_watts)

    total_energy_kwh = round(sum(adjusted_watt_hours.values()) / 1000, 3)
    peak_power_w = round(max(adjusted_watts.values(), default=0.0), 1)

    return {
        "entity_id": dataset.entity_id,
        "native_state": dataset.native_state,
        "adjusted_energy_kwh": total_energy_kwh,
        "adjusted_peak_power_w": peak_power_w,
        "watts": adjusted_watts,
        "wh_period": adjusted_watt_hours,
        "mean_factor": round(mean(factors), 3) if factors else None,
    }


def _factor_for_timestamp(observer: Observer, timestamp: datetime, config: ModelConfig) -> float:
    """Calculate the model factor for a specific timestamp."""
    azimuth = solar_azimuth(observer, timestamp)
    elevation = solar_elevation(observer, timestamp)
    return calculate_current_factor(azimuth=azimuth, elevation=elevation, config=config)


def _morning_factor(azimuth: float, config: ModelConfig) -> float:
    """Morning azimuth-dependent shading factor."""
    if azimuth <= config.morning_free_azimuth:
        return 1.0

    if azimuth <= config.morning_shade_start_azimuth:
        return _lerp(
            azimuth,
            config.morning_free_azimuth,
            config.morning_shade_start_azimuth,
            1.0,
            0.85,
        )

    if azimuth <= config.morning_shade_end_azimuth:
        return _lerp(
            azimuth,
            config.morning_shade_start_azimuth,
            config.morning_shade_end_azimuth,
            0.85,
            config.morning_deep_factor,
        )

    if azimuth <= config.morning_recover_azimuth:
        return _lerp(
            azimuth,
            config.morning_shade_end_azimuth,
            config.morning_recover_azimuth,
            config.morning_deep_factor,
            1.0,
        )

    return 1.0


def _afternoon_factor(azimuth: float, elevation: float, config: ModelConfig) -> float:
    """Afternoon elevation-dependent shading factor."""
    if config.after_solar_noon_only and azimuth <= 180:
        return 1.0

    if elevation >= config.afternoon_high_elevation:
        return 1.0

    if elevation >= config.afternoon_mid_elevation:
        return _lerp(
            elevation,
            config.afternoon_mid_elevation,
            config.afternoon_high_elevation,
            config.afternoon_mid_factor,
            1.0,
        )

    if elevation >= config.afternoon_low_elevation:
        return _lerp(
            elevation,
            config.afternoon_low_elevation,
            config.afternoon_mid_elevation,
            config.afternoon_low_factor,
            config.afternoon_mid_factor,
        )

    if elevation >= config.afternoon_deep_elevation:
        return _lerp(
            elevation,
            config.afternoon_deep_elevation,
            config.afternoon_low_elevation,
            config.afternoon_deep_factor,
            config.afternoon_low_factor,
        )

    if elevation >= config.afternoon_end_elevation:
        return _lerp(
            elevation,
            config.afternoon_end_elevation,
            config.afternoon_deep_elevation,
            config.afternoon_end_factor,
            config.afternoon_deep_factor,
        )

    return config.afternoon_horizon_factor


def _derive_watt_hours_from_watts(adjusted_watts: dict[str, float]) -> dict[str, float]:
    """Derive per-period energy from a power curve using the median time step."""
    if len(adjusted_watts) < 2:
        return {}

    timestamps = [datetime.fromisoformat(timestamp) for timestamp in adjusted_watts]
    deltas = [
        int((timestamps[index + 1] - timestamps[index]).total_seconds())
        for index in range(len(timestamps) - 1)
    ]
    median_delta_seconds = sorted(deltas)[len(deltas) // 2]
    hours = median_delta_seconds / 3600

    return {
        timestamp: round(power * hours, 3)
        for timestamp, power in adjusted_watts.items()
    }


def _lerp(value: float, start: float, end: float, out_start: float, out_end: float) -> float:
    """Linearly interpolate between two values."""
    if start == end:
        return out_end

    ratio = (value - start) / (end - start)
    ratio = min(max(ratio, 0.0), 1.0)
    return out_start + ratio * (out_end - out_start)
