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
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
from statistics import median
from typing import Any

from .model import calculate_current_factor

from astral import Observer
from astral.sun import azimuth as solar_azimuth
from astral.sun import elevation as solar_elevation

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import (
    CALIBRATION_BATTERY_IDLE_WATTS,
    CALIBRATION_CLIP_MARGIN,
    CALIBRATION_ENVELOPE_PERCENTILE,
    CALIBRATION_MAX_CURTAILMENT_RATIO,
    CALIBRATION_MAX_FACTOR,
    CALIBRATION_MAX_SPREAD,
    CALIBRATION_MIN_BUCKET_SAMPLES,
    CALIBRATION_MIN_EXPECTED_WATTS,
    CALIBRATION_REFERENCE_MIN_MODEL_FACTOR,
    CALIBRATION_REFERENCE_MIN_SAMPLES,
    CONF_ACTUAL_PRODUCTION_ENTITY,
    CONF_BATTERY_FULL_ENTITY,
    CONF_BATTERY_FULL_THRESHOLD,
    CONF_BATTERY_POWER_ENTITY,
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
    band: str | None


@dataclass(slots=True)
class BucketSuggestion:
    """Observed factor for one model bucket.

    ``observed_factor`` is normalized against the unshaded reference (so it is
    corrected for forecast bias); ``raw_factor`` is the uncorrected median.
    ``spread`` is the interquartile range of the raw ratios -- a wide spread
    means weather/noise dominates and the suggestion should not be trusted.
    """

    parameter: str
    observed_factor: float | None
    raw_factor: float | None
    spread: float | None
    sample_count: int
    configured_factor: float | None
    curtailment_ratio: float | None = field(default=None)
    confident: bool = field(default=False)

    def as_dict(self) -> dict[str, Any]:
        """Serialize for service response / diagnostics."""
        return {
            "parameter": self.parameter,
            "observed_factor": self.observed_factor,
            "raw_factor": self.raw_factor,
            "configured_factor": self.configured_factor,
            "spread": self.spread,
            "curtailment_ratio": self.curtailment_ratio,
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
    battery_power_entity = config.get(CONF_BATTERY_POWER_ENTITY)
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
        battery_power_entity=battery_power_entity,
    )

    observer = Observer(
        latitude=hass.config.latitude,
        longitude=hass.config.longitude,
        elevation=hass.config.elevation,
    )

    samples, stats, band_curtailed = _build_samples(
        observer=observer,
        model=model,
        forecast_states=histories["forecast"],
        actual_states=histories["actual"],
        battery_states=histories.get("battery"),
        battery_power_states=histories.get("battery_power"),
        clip_watts=clip_watts,
        battery_threshold=battery_threshold,
    )

    suggestions, reference = _summarize(samples, model, band_curtailed)

    curtail_note = (
        "Curtailed samples were excluded: battery full (raw PV is then clamped to "
        f"the ~{clip_watts:g} W AC cap), or raw PV at the cap while the battery is "
        "not absorbing. Uncurtailed samples above the cap (battery charging) are "
        "kept."
    )

    return {
        "window_days": window_days,
        "clip_watts": clip_watts,
        "actual_entity": actual_entity,
        "forecast_entity": forecast_entity,
        "generated_at": end.isoformat(),
        "sample_stats": stats,
        "reference": reference,
        "suggestions": [s.as_dict() for s in suggestions],
        "note": (
            "Analysis only -- observed factors are the upper envelope (P"
            f"{int(CALIBRATION_ENVELOPE_PERCENTILE * 100)}) of actual/forecast, "
            "normalized against the unshaded reference, and never applied. "
            f"{curtail_note} Trust rows where confident=true."
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
    battery_power_entity: str | None,
) -> dict[str, list[Any]]:
    """Fetch recorder history for the entities involved in calibration."""
    try:
        from homeassistant.components.recorder import get_instance, history
    except ImportError as err:  # pragma: no cover - recorder always present in HA
        raise CalibrationError("The Recorder integration is not available.") from err

    entity_ids = [forecast_entity, actual_entity]
    if battery_entity:
        entity_ids.append(battery_entity)
    if battery_power_entity:
        entity_ids.append(battery_power_entity)

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
    if battery_power_entity:
        result["battery_power"] = states.get(battery_power_entity) or []
    return result


def _build_samples(
    *,
    observer: Observer,
    model: ModelConfig,
    forecast_states: list[Any],
    actual_states: list[Any],
    battery_states: list[Any] | None,
    battery_power_states: list[Any] | None,
    clip_watts: float,
    battery_threshold: float,
) -> tuple[list[_Sample], dict[str, int], dict[str, int]]:
    """Align actual production against expected power, filtering curtailment.

    Also tracks, per band, how many samples were dropped for curtailment/battery
    so the caller can tell when a band's clear-sky peaks are missing.
    """
    forecast_curves = _forecast_curves(forecast_states)
    forecast_times = [when for when, _ in forecast_curves]
    battery_series = _numeric_series(battery_states) if battery_states else []
    battery_times = [when for when, _ in battery_series]
    # Battery power distinguishes a raw PV value at the AC cap that is curtailed
    # (battery full, not absorbing) from one that is genuine (battery charging).
    power_series = _numeric_series(battery_power_states) if battery_power_states else []
    power_times = [when for when, _ in power_series]

    clip_limit = clip_watts * CALIBRATION_CLIP_MARGIN

    samples: list[_Sample] = []
    band_curtailed: dict[str, int] = defaultdict(int)
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

        elevation = solar_elevation(observer, when)
        if elevation <= 0:
            stats["skipped_invalid"] += 1
            continue
        azimuth = solar_azimuth(observer, when)
        band = _classify(azimuth, elevation, model)

        # Curtailment samples are dropped, but recorded per band: a band that
        # loses its clear-sky peaks this way cannot be trusted.
        #
        # 1) Battery full -> the only PV path is the capped AC output, so raw PV
        #    is clamped and hides the true generation.
        if battery_series:
            soc = _value_at(battery_times, battery_series, when)
            if soc is not None and soc >= battery_threshold:
                stats["skipped_battery_full"] += 1
                if band is not None:
                    band_curtailed[band] += 1
                continue

        # 2) Raw PV pinned at the AC cap while the battery is not absorbing power
        #    is curtailment too (catches a lagging/again-below-100 SoC reading).
        #    Raw PV above the cap *while charging* is genuine and kept.
        if power_series and actual >= clip_limit:
            power = _value_at(power_times, power_series, when)
            if power is not None and abs(power) <= CALIBRATION_BATTERY_IDLE_WATTS:
                stats["skipped_curtailed"] += 1
                if band is not None:
                    band_curtailed[band] += 1
                continue

        curve = _curve_at(forecast_times, forecast_curves, when)
        if curve is None:
            stats["skipped_no_forecast"] += 1
            continue

        expected = _interpolate_curve(curve, when)
        if expected is None or expected < CALIBRATION_MIN_EXPECTED_WATTS:
            stats["skipped_low_expected"] += 1
            continue

        samples.append(
            _Sample(
                when=when,
                azimuth=azimuth,
                elevation=elevation,
                factor=actual / expected,
                band=band,
            )
        )
        stats["used"] += 1

    return samples, stats, dict(band_curtailed)


def _classify(azimuth: float, elevation: float, model: ModelConfig) -> str | None:
    """Assign a sample to a calibration bucket (or the unshaded reference)."""
    if (
        calculate_current_factor(azimuth=azimuth, elevation=elevation, config=model)
        >= CALIBRATION_REFERENCE_MIN_MODEL_FACTOR
    ):
        return "reference"
    if (
        azimuth <= 180
        and model.morning_shade_start_azimuth <= azimuth <= model.morning_recover_azimuth
    ):
        return "morning_deep_factor"
    if azimuth > 180:
        return _afternoon_band(elevation, model)
    return None


def _summarize(
    samples: list[_Sample], model: ModelConfig, band_curtailed: dict[str, int]
) -> tuple[list[BucketSuggestion], dict[str, Any]]:
    """Reduce samples to per-parameter observed factors, normalized to baseline."""
    reference: list[float] = []
    band_values: dict[str, list[float]] = defaultdict(list)

    for sample in samples:
        if sample.band == "reference":
            reference.append(sample.factor)
        elif sample.band is not None:
            band_values[sample.band].append(sample.factor)

    reference_factor = (
        _percentile(reference, CALIBRATION_ENVELOPE_PERCENTILE)
        if len(reference) >= CALIBRATION_REFERENCE_MIN_SAMPLES
        else None
    )
    reference_info = {
        "factor": round(reference_factor, 3) if reference_factor else None,
        "median": round(median(reference), 3) if reference else None,
        "sample_count": len(reference),
        "applied": reference_factor is not None,
        "note": (
            "Unshaded upper-envelope baseline used to correct forecast bias. If "
            "this is well below 1.0, the base forecast likely over-predicts "
            "(check its declared kWp/tilt/azimuth)."
            if reference_factor is not None
            else "Too few unshaded samples; factors are not bias-corrected."
        ),
    }

    configured = {
        "morning_deep_factor": model.morning_deep_factor,
        "afternoon_mid_factor": model.afternoon_mid_factor,
        "afternoon_low_factor": model.afternoon_low_factor,
        "afternoon_deep_factor": model.afternoon_deep_factor,
        "afternoon_end_factor": model.afternoon_end_factor,
        "afternoon_horizon_factor": model.afternoon_horizon_factor,
    }
    suggestions = [
        _bucket_suggestion(
            parameter,
            band_values.get(parameter, []),
            configured_factor,
            reference_factor,
            band_curtailed.get(parameter, 0),
        )
        for parameter, configured_factor in configured.items()
    ]
    return suggestions, reference_info


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
    parameter: str,
    values: list[float],
    configured: float,
    reference_factor: float | None,
    curtailed_count: int,
) -> BucketSuggestion:
    """Build a suggestion from a bucket's observed factors.

    The estimator is the upper envelope (a high percentile) of actual/forecast,
    because clouds and curtailment only push production below the true shading
    ceiling. It is divided by the unshaded reference (when available) so the
    factor is expressed relative to the observed baseline rather than the raw
    forecast, then clamped to [0, 1]. A suggestion is only ``confident`` with
    enough samples, a tight interquartile spread, and a low share of its samples
    lost to curtailment -- otherwise the clear-sky peaks it needs are missing.
    """
    if not values:
        return BucketSuggestion(
            parameter, None, None, None, 0, configured, curtailment_ratio=None
        )

    raw = _percentile(values, CALIBRATION_ENVELOPE_PERCENTILE)
    spread = _iqr(values)
    if reference_factor and reference_factor > 0:
        normalized = raw / reference_factor
    else:
        normalized = raw
    normalized = min(max(normalized, 0.0), CALIBRATION_MAX_FACTOR)

    total = len(values) + curtailed_count
    curtailment_ratio = curtailed_count / total if total else 0.0
    confident = (
        len(values) >= CALIBRATION_MIN_BUCKET_SAMPLES
        and spread <= CALIBRATION_MAX_SPREAD
        and curtailment_ratio <= CALIBRATION_MAX_CURTAILMENT_RATIO
    )
    return BucketSuggestion(
        parameter=parameter,
        observed_factor=round(normalized, 3),
        raw_factor=round(raw, 3),
        spread=round(spread, 3),
        sample_count=len(values),
        configured_factor=configured,
        curtailment_ratio=round(curtailment_ratio, 2),
        confident=confident,
    )


def _iqr(values: list[float]) -> float:
    """Interquartile range (P75 - P25) as a simple dispersion measure."""
    if len(values) < 2:
        return 0.0
    ordered = sorted(values)
    n = len(ordered)
    lower = ordered[: n // 2]
    upper = ordered[(n + 1) // 2 :]
    return median(upper) - median(lower)


def _percentile(values: list[float], fraction: float) -> float:
    """Linear-interpolated percentile (``fraction`` in [0, 1]) of ``values``."""
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    pos = fraction * (len(ordered) - 1)
    low = int(pos)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (pos - low) * (ordered[high] - ordered[low])


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
