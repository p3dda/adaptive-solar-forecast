"""Recorder-based calibration for Adaptive Solar Forecast.

This module derives *observed* shading factors by comparing the historical base
forecast against actual measured production, bucketed by sun position. It is
analysis-only: the result is a set of suggestions the user can compare against
their tuned ``ModelConfig``; it never overwrites the configured parameters.

Curtailment handling is essential here. A Balkonkraftwerk inverter clamps its
output (commonly to 800 W) once the battery is full, mostly in the afternoon.
Those samples reflect a legal/hardware cap, not shading, so they are excluded
before any factor is computed -- otherwise curtailment would be misread as
afternoon shading and wrongly damp the forecast.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from statistics import median
from typing import Any

from astral import Observer
from astral.sun import azimuth as solar_azimuth
from astral.sun import elevation as solar_elevation

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import (
    CALIBRATION_CLIP_MARGIN,
    CALIBRATION_MAX_FACTOR,
    CALIBRATION_MIN_BUCKET_SAMPLES,
    CALIBRATION_MIN_EXPECTED_WATTS,
    CONF_ACTUAL_PRODUCTION_ENTITY,
    CONF_BATTERY_FULL_ENTITY,
    CONF_BATTERY_FULL_THRESHOLD,
    CONF_CALIBRATION_CLIP_WATTS,
    CONF_CALIBRATION_DAYS,
    CONF_FORECAST_TODAY_ENTITY,
    DEFAULT_BATTERY_FULL_THRESHOLD,
    DEFAULT_CALIBRATION_CLIP_WATTS,
    DEFAULT_CALIBRATION_DAYS,
)
from .model import ModelConfig

_LOGGER = logging.getLogger(__name__)


class CalibrationError(Exception):
    """Raised when calibration cannot be performed."""


@dataclass(slots=True)
class _Sample:
    """A single aligned actual-vs-expected observation."""

    when: datetime
    azimuth: float
    elevation: float
    factor: float


@dataclass(slots=True)
class BucketSuggestion:
    """Observed factor for one model bucket."""

    parameter: str
    observed_factor: float | None
    sample_count: int
    configured_factor: float | None
    confident: bool = field(default=False)

    def as_dict(self) -> dict[str, Any]:
        """Serialize for service response / diagnostics."""
        return {
            "parameter": self.parameter,
            "observed_factor": self.observed_factor,
            "configured_factor": self.configured_factor,
            "sample_count": self.sample_count,
            "confident": self.confident,
        }


async def async_run_calibration(
    hass: HomeAssistant,
    config: dict[str, Any],
    model: ModelConfig,
    *,
    days: int | None = None,
) -> dict[str, Any]:
    """Run a calibration pass and return suggestions (never applies them)."""
    actual_entity = config.get(CONF_ACTUAL_PRODUCTION_ENTITY)
    if not actual_entity:
        raise CalibrationError(
            "No actual production entity configured. Set one in the integration "
            "options before calibrating."
        )
    forecast_entity = config.get(CONF_FORECAST_TODAY_ENTITY)
    if not forecast_entity:
        raise CalibrationError("No base forecast entity configured.")

    window_days = int(days or config.get(CONF_CALIBRATION_DAYS, DEFAULT_CALIBRATION_DAYS))
    clip_watts = float(config.get(CONF_CALIBRATION_CLIP_WATTS, DEFAULT_CALIBRATION_CLIP_WATTS))
    battery_entity = config.get(CONF_BATTERY_FULL_ENTITY)
    battery_threshold = float(
        config.get(CONF_BATTERY_FULL_THRESHOLD, DEFAULT_BATTERY_FULL_THRESHOLD)
    )

    end = dt_util.utcnow()
    start = end - timedelta(days=window_days)

    histories = await _fetch_history(
        hass,
        start,
        end,
        forecast_entity=forecast_entity,
        actual_entity=actual_entity,
        battery_entity=battery_entity,
    )

    observer = Observer(
        latitude=hass.config.latitude,
        longitude=hass.config.longitude,
        elevation=hass.config.elevation,
    )

    samples, stats = _build_samples(
        observer=observer,
        forecast_states=histories["forecast"],
        actual_states=histories["actual"],
        battery_states=histories.get("battery"),
        clip_watts=clip_watts,
        battery_threshold=battery_threshold,
    )

    suggestions = _summarize(samples, model)

    return {
        "window_days": window_days,
        "clip_watts": clip_watts,
        "actual_entity": actual_entity,
        "forecast_entity": forecast_entity,
        "generated_at": end.isoformat(),
        "sample_stats": stats,
        "suggestions": [s.as_dict() for s in suggestions],
        "note": (
            "Analysis only -- these are observed factors from history, not applied. "
            "Curtailed samples (>= "
            f"{clip_watts:g} W, or battery full) were excluded."
        ),
    }


async def _fetch_history(
    hass: HomeAssistant,
    start: datetime,
    end: datetime,
    *,
    forecast_entity: str,
    actual_entity: str,
    battery_entity: str | None,
) -> dict[str, list[Any]]:
    """Fetch recorder history for the entities involved in calibration."""
    try:
        from homeassistant.components.recorder import get_instance, history
    except ImportError as err:  # pragma: no cover - recorder always present in HA
        raise CalibrationError("The Recorder integration is not available.") from err

    entity_ids = [forecast_entity, actual_entity]
    if battery_entity:
        entity_ids.append(battery_entity)

    states = await get_instance(hass).async_add_executor_job(
        history.get_significant_states,
        hass,
        start,
        end,
        entity_ids,
        None,  # filters
        True,  # include_start_time_state
        True,  # significant_changes_only
        False,  # minimal_response -- we need attributes / State objects
        False,  # no_attributes
    )

    forecast_states = states.get(forecast_entity) or []
    actual_states = states.get(actual_entity) or []
    if not forecast_states:
        raise CalibrationError(
            f"No recorder history for forecast entity {forecast_entity}."
        )
    if not actual_states:
        raise CalibrationError(
            f"No recorder history for actual production entity {actual_entity}."
        )

    result: dict[str, list[Any]] = {
        "forecast": forecast_states,
        "actual": actual_states,
    }
    if battery_entity:
        result["battery"] = states.get(battery_entity) or []
    return result


def _build_samples(
    *,
    observer: Observer,
    forecast_states: list[Any],
    actual_states: list[Any],
    battery_states: list[Any] | None,
    clip_watts: float,
    battery_threshold: float,
) -> tuple[list[_Sample], dict[str, int]]:
    """Align actual production against expected power, filtering curtailment."""
    forecast_curves = _forecast_curves(forecast_states)
    forecast_times = [when for when, _ in forecast_curves]
    battery_series = _numeric_series(battery_states) if battery_states else []
    battery_times = [when for when, _ in battery_series]

    clip_limit = clip_watts * CALIBRATION_CLIP_MARGIN

    samples: list[_Sample] = []
    stats = {
        "considered": 0,
        "used": 0,
        "skipped_curtailed": 0,
        "skipped_battery_full": 0,
        "skipped_no_forecast": 0,
        "skipped_low_expected": 0,
        "skipped_invalid": 0,
    }

    for when, actual in _numeric_series(actual_states):
        stats["considered"] += 1

        if actual >= clip_limit:
            stats["skipped_curtailed"] += 1
            continue

        if battery_series:
            soc = _value_at(battery_times, battery_series, when)
            if soc is not None and soc >= battery_threshold:
                stats["skipped_battery_full"] += 1
                continue

        curve = _curve_at(forecast_times, forecast_curves, when)
        if curve is None:
            stats["skipped_no_forecast"] += 1
            continue

        expected = _interpolate_curve(curve, when)
        if expected is None or expected < CALIBRATION_MIN_EXPECTED_WATTS:
            stats["skipped_low_expected"] += 1
            continue

        elevation = solar_elevation(observer, when)
        if elevation <= 0:
            stats["skipped_invalid"] += 1
            continue

        azimuth = solar_azimuth(observer, when)
        samples.append(
            _Sample(
                when=when,
                azimuth=azimuth,
                elevation=elevation,
                factor=actual / expected,
            )
        )
        stats["used"] += 1

    return samples, stats


def _summarize(samples: list[_Sample], model: ModelConfig) -> list[BucketSuggestion]:
    """Reduce samples to per-parameter observed factors."""
    morning: list[float] = []
    afternoon_bands: dict[str, list[float]] = {
        "afternoon_mid_factor": [],
        "afternoon_low_factor": [],
        "afternoon_deep_factor": [],
        "afternoon_end_factor": [],
        "afternoon_horizon_factor": [],
    }

    for sample in samples:
        # Morning: sun in the east (azimuth below solar noon) inside the shaded sector.
        if (
            sample.azimuth <= 180
            and model.morning_shade_start_azimuth
            <= sample.azimuth
            <= model.morning_recover_azimuth
        ):
            morning.append(sample.factor)
            continue

        # Afternoon: west of solar noon, bucketed by elevation band.
        if sample.azimuth > 180:
            band = _afternoon_band(sample.elevation, model)
            if band is not None:
                afternoon_bands[band].append(sample.factor)

    suggestions: list[BucketSuggestion] = [
        _bucket_suggestion("morning_deep_factor", morning, model.morning_deep_factor),
    ]
    configured = {
        "afternoon_mid_factor": model.afternoon_mid_factor,
        "afternoon_low_factor": model.afternoon_low_factor,
        "afternoon_deep_factor": model.afternoon_deep_factor,
        "afternoon_end_factor": model.afternoon_end_factor,
        "afternoon_horizon_factor": model.afternoon_horizon_factor,
    }
    for parameter, values in afternoon_bands.items():
        suggestions.append(
            _bucket_suggestion(parameter, values, configured[parameter])
        )
    return suggestions


def _afternoon_band(elevation: float, model: ModelConfig) -> str | None:
    """Map an elevation to the afternoon model band it falls into."""
    if elevation >= model.afternoon_high_elevation:
        return None  # unshaded reference region
    if elevation >= model.afternoon_mid_elevation:
        return "afternoon_mid_factor"
    if elevation >= model.afternoon_low_elevation:
        return "afternoon_low_factor"
    if elevation >= model.afternoon_deep_elevation:
        return "afternoon_deep_factor"
    if elevation >= model.afternoon_end_elevation:
        return "afternoon_end_factor"
    return "afternoon_horizon_factor"


def _bucket_suggestion(
    parameter: str, values: list[float], configured: float
) -> BucketSuggestion:
    """Build a suggestion from a bucket's observed factors."""
    if not values:
        return BucketSuggestion(parameter, None, 0, configured, confident=False)
    observed = min(median(values), CALIBRATION_MAX_FACTOR)
    return BucketSuggestion(
        parameter,
        round(observed, 3),
        len(values),
        configured,
        confident=len(values) >= CALIBRATION_MIN_BUCKET_SAMPLES,
    )


def _forecast_curves(states: list[Any]) -> list[tuple[datetime, dict[datetime, float]]]:
    """Extract published forecast power curves keyed by publication time."""
    curves: list[tuple[datetime, dict[datetime, float]]] = []
    for state in states:
        raw = getattr(state, "attributes", {}).get("watts")
        curve = _normalize_curve(raw)
        if curve:
            curves.append((_as_utc(state.last_changed), curve))
    curves.sort(key=lambda item: item[0])
    return curves


def _normalize_curve(raw: Any) -> dict[datetime, float]:
    """Parse a ``watts`` attribute dict into a datetime->power mapping."""
    if not isinstance(raw, dict):
        return {}
    curve: dict[datetime, float] = {}
    for key, value in raw.items():
        parsed = dt_util.parse_datetime(str(key))
        if parsed is None:
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt_util.UTC)
        try:
            curve[parsed] = float(value)
        except (TypeError, ValueError):
            continue
    return dict(sorted(curve.items()))


def _numeric_series(states: list[Any] | None) -> list[tuple[datetime, float]]:
    """Parse a numeric state history into sorted (time, value) pairs."""
    series: list[tuple[datetime, float]] = []
    for state in states or []:
        raw = getattr(state, "state", None)
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue  # skip unknown/unavailable
        series.append((_as_utc(state.last_changed), value))
    series.sort(key=lambda item: item[0])
    return series


def _curve_at(
    times: list[datetime],
    curves: list[tuple[datetime, dict[datetime, float]]],
    when: datetime,
) -> dict[datetime, float] | None:
    """Return the most recent forecast curve published at or before ``when``."""
    index = bisect_right(times, when) - 1
    if index < 0:
        return None
    return curves[index][1]


def _value_at(
    times: list[datetime],
    series: list[tuple[datetime, float]],
    when: datetime,
) -> float | None:
    """Return the most recent value at or before ``when``."""
    index = bisect_right(times, when) - 1
    if index < 0:
        return None
    return series[index][1]


def _interpolate_curve(curve: dict[datetime, float], when: datetime) -> float | None:
    """Linearly interpolate expected power at ``when`` within a forecast curve."""
    keys = list(curve)
    index = bisect_right(keys, when)
    if index == 0 or index >= len(keys):
        return None  # outside the curve's covered range
    left, right = keys[index - 1], keys[index]
    span = (right - left).total_seconds()
    if span <= 0:
        return curve[left]
    ratio = (when - left).total_seconds() / span
    return curve[left] + ratio * (curve[right] - curve[left])


def _as_utc(value: datetime) -> datetime:
    """Coerce a datetime to timezone-aware UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=dt_util.UTC)
    return dt_util.as_utc(value)
