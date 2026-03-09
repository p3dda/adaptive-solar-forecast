"""Sensor platform for Adaptive Solar Forecast."""

from __future__ import annotations

from typing import Any

from dataclasses import asdict, dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AdaptiveSolarForecastCoordinator


@dataclass(slots=True)
class AdaptiveSolarForecastSensorDescription(SensorEntityDescription):
    """Description for Adaptive Solar Forecast sensors."""

    pass


SENSOR_DESCRIPTIONS = (
    AdaptiveSolarForecastSensorDescription(
        key="today_energy",
        name="Adjusted Energy Today",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    ),
    AdaptiveSolarForecastSensorDescription(
        key="tomorrow_energy",
        name="Adjusted Energy Tomorrow",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    ),
    AdaptiveSolarForecastSensorDescription(
        key="current_factor",
        name="Current Shading Factor",
        native_unit_of_measurement=None,
    ),
    AdaptiveSolarForecastSensorDescription(
        key="today_peak_power",
        name="Adjusted Peak Power Today",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Adaptive Solar Forecast sensors from a config entry."""
    coordinator: AdaptiveSolarForecastCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        AdaptiveSolarForecastSensor(coordinator, entry, description)
        for description in SENSOR_DESCRIPTIONS
    )


class AdaptiveSolarForecastSensor(CoordinatorEntity[AdaptiveSolarForecastCoordinator], SensorEntity):
    """Representation of an Adaptive Solar Forecast sensor."""

    entity_description: AdaptiveSolarForecastSensorDescription

    def __init__(
        self,
        coordinator: AdaptiveSolarForecastCoordinator,
        entry: ConfigEntry,
        description: AdaptiveSolarForecastSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_name = f"{entry.title} {description.name}"
        self._attr_has_entity_name = False
        self._attr_device_class = description.device_class
        self._attr_native_unit_of_measurement = description.native_unit_of_measurement
        self._attr_state_class = description.state_class
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "OpenAI",
            "model": "Adaptive Solar Forecast MVP",
        }

    @property
    def native_value(self) -> float | None:
        """Return the sensor value."""
        data = self.coordinator.data
        if self.entity_description.key == "today_energy":
            return data["today"]["adjusted_energy_kwh"]
        if self.entity_description.key == "tomorrow_energy":
            tomorrow = data["tomorrow"]
            return tomorrow["adjusted_energy_kwh"] if tomorrow else None
        if self.entity_description.key == "current_factor":
            return round(data["current_factor"], 3)
        if self.entity_description.key == "today_peak_power":
            return data["today"]["adjusted_peak_power_w"]
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        data = self.coordinator.data
        base = {
            "current_azimuth": round(data["current_azimuth"], 2),
            "current_elevation": round(data["current_elevation"], 2),
            "model": asdict(data["model"]),
        }

        if self.entity_description.key == "today_energy":
            base["watts"] = data["today"]["watts"]
            base["wh_period"] = data["today"]["wh_period"]
            base["mean_factor"] = data["today"]["mean_factor"]
            base["source_entity_id"] = data["today"]["entity_id"]
        elif self.entity_description.key == "tomorrow_energy" and data["tomorrow"]:
            base["watts"] = data["tomorrow"]["watts"]
            base["wh_period"] = data["tomorrow"]["wh_period"]
            base["mean_factor"] = data["tomorrow"]["mean_factor"]
            base["source_entity_id"] = data["tomorrow"]["entity_id"]

        return base
