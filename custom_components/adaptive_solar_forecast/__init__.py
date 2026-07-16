"""The Adaptive Solar Forecast integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .calibration import CalibrationError, async_run_calibration
from .const import DOMAIN, SERVICE_CALIBRATE
from .coordinator import AdaptiveSolarForecastCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]

ATTR_CONFIG_ENTRY_ID = "config_entry_id"
ATTR_DAYS = "days"

CALIBRATE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Optional(ATTR_DAYS): vol.All(vol.Coerce(int), vol.Range(min=1, max=90)),
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Adaptive Solar Forecast from a config entry."""
    coordinator = AdaptiveSolarForecastCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    _async_register_services(hass)
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when its options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload an Adaptive Solar Forecast config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_CALIBRATE)
    return unloaded


def _async_register_services(hass: HomeAssistant) -> None:
    """Register integration services once."""
    if hass.services.has_service(DOMAIN, SERVICE_CALIBRATE):
        return

    async def _handle_calibrate(call: ServiceCall) -> ServiceResponse:
        coordinator = _resolve_coordinator(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        try:
            result = await async_run_calibration(
                hass,
                coordinator.config,
                coordinator.model,
                days=call.data.get(ATTR_DAYS),
            )
        except CalibrationError as err:
            raise HomeAssistantError(str(err)) from err
        coordinator.last_calibration = result
        return result

    hass.services.async_register(
        DOMAIN,
        SERVICE_CALIBRATE,
        _handle_calibrate,
        schema=CALIBRATE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )


def _resolve_coordinator(
    hass: HomeAssistant, entry_id: str | None
) -> AdaptiveSolarForecastCoordinator:
    """Find the coordinator to calibrate, requiring an id when ambiguous."""
    coordinators: dict[str, AdaptiveSolarForecastCoordinator] = hass.data.get(DOMAIN, {})
    if not coordinators:
        raise HomeAssistantError("No Adaptive Solar Forecast entries are set up.")

    if entry_id is not None:
        coordinator = coordinators.get(entry_id)
        if coordinator is None:
            raise HomeAssistantError(f"Unknown config entry id: {entry_id}")
        return coordinator

    if len(coordinators) > 1:
        raise HomeAssistantError(
            "Multiple Adaptive Solar Forecast entries exist; pass config_entry_id."
        )
    return next(iter(coordinators.values()))
