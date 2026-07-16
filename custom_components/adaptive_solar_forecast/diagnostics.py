"""Diagnostics support for Adaptive Solar Forecast."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.redact import async_redact_data

from .const import DOMAIN
from .coordinator import AdaptiveSolarForecastCoordinator

TO_REDACT: set[str] = set()


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: AdaptiveSolarForecastCoordinator | None = hass.data.get(DOMAIN, {}).get(entry.entry_id)

    data = coordinator.data if coordinator else None
    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": async_redact_data(dict(entry.options), TO_REDACT),
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success if coordinator else None,
            "last_update_exception": (
                str(coordinator.last_update_exception) if coordinator and coordinator.last_update_exception else None
            ),
            "update_interval_seconds": (
                int(coordinator.update_interval.total_seconds())
                if coordinator and coordinator.update_interval
                else None
            ),
        },
        "data": _summarize_data(data),
        "last_calibration": coordinator.last_calibration if coordinator else None,
    }


def _summarize_data(data: Any) -> dict[str, Any] | None:
    """Summarize coordinator data without large timeseries payloads."""
    if not isinstance(data, dict):
        return None

    return {
        "model": _model_as_dict(data.get("model")),
        "current_factor": data.get("current_factor"),
        "current_azimuth": data.get("current_azimuth"),
        "current_elevation": data.get("current_elevation"),
        "today": _summarize_dataset(data.get("today")),
        "tomorrow": _summarize_dataset(data.get("tomorrow")),
    }


def _summarize_dataset(dataset: Any) -> dict[str, Any] | None:
    """Summarize adjusted dataset details."""
    if not isinstance(dataset, dict):
        return None

    watts = dataset.get("watts") or {}
    wh_period = dataset.get("wh_period") or {}
    return {
        "entity_id": dataset.get("entity_id"),
        "native_state": dataset.get("native_state"),
        "adjusted_energy_kwh": dataset.get("adjusted_energy_kwh"),
        "adjusted_peak_power_w": dataset.get("adjusted_peak_power_w"),
        "mean_factor": dataset.get("mean_factor"),
        "watts_points": len(watts) if isinstance(watts, dict) else None,
        "wh_period_points": len(wh_period) if isinstance(wh_period, dict) else None,
        "watts_range": _range_summary(watts),
        "wh_period_range": _range_summary(wh_period),
    }


def _range_summary(series: Any) -> dict[str, Any] | None:
    """Return first/last keys for a dict-like series."""
    if not isinstance(series, dict) or not series:
        return None
    keys = sorted(series.keys())
    return {"start": keys[0], "end": keys[-1]}


def _model_as_dict(model: Any) -> dict[str, Any] | None:
    """Render the model config safely for diagnostics."""
    if model is None:
        return None
    if is_dataclass(model):
        return asdict(model)
    if isinstance(model, dict):
        return dict(model)
    return {"value": model}
