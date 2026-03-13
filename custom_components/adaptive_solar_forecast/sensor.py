"""Sensor platform for Adaptive Solar Forecast."""

from __future__ import annotations

from typing import Any

from dataclasses import asdict, dataclass, is_dataclass

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
        data = self._get_coordinator_data()
        if data is None:
            return None
        today = self._get_dataset(data, "today")
        tomorrow = self._get_dataset(data, "tomorrow")
        if self.entity_description.key == "today_energy":
            return today.get("adjusted_energy_kwh") if today else None
        if self.entity_description.key == "tomorrow_energy":
            return tomorrow.get("adjusted_energy_kwh") if tomorrow else None
        if self.entity_description.key == "current_factor":
            current_factor = data.get("current_factor")
            return round(current_factor, 3) if isinstance(current_factor, (int, float)) else None
        if self.entity_description.key == "today_peak_power":
            return today.get("adjusted_peak_power_w") if today else None
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra attributes."""
        data = self._get_coordinator_data()
        if data is None:
            return {}
        today = self._get_dataset(data, "today")
        tomorrow = self._get_dataset(data, "tomorrow")
        model = self._model_as_dict(data.get("model"))
        base = {
            "current_azimuth": self._round_if_number(data.get("current_azimuth"), 2),
            "current_elevation": self._round_if_number(data.get("current_elevation"), 2),
            "model": model,
        }

        if self.entity_description.key == "today_energy" and today:
            base["watts"] = today.get("watts")
            base["wh_period"] = today.get("wh_period")
            base["mean_factor"] = today.get("mean_factor")
            base["source_entity_id"] = today.get("entity_id")
        elif self.entity_description.key == "tomorrow_energy" and tomorrow:
            base["watts"] = tomorrow.get("watts")
            base["wh_period"] = tomorrow.get("wh_period")
            base["mean_factor"] = tomorrow.get("mean_factor")
            base["source_entity_id"] = tomorrow.get("entity_id")

        return base

    @staticmethod
    def _round_if_number(value: Any, digits: int) -> float | None:
        """Round numeric values defensively."""
        return round(value, digits) if isinstance(value, (int, float)) else None

    def _get_coordinator_data(self) -> dict[str, Any] | None:
        """Return coordinator data if it has the expected mapping structure."""
        data = self.coordinator.data
        return data if isinstance(data, dict) else None

    @staticmethod
    def _get_dataset(data: dict[str, Any], key: str) -> dict[str, Any] | None:
        """Fetch a dataset dict from coordinator data."""
        dataset = data.get(key)
        return dataset if isinstance(dataset, dict) else None

    @staticmethod
    def _model_as_dict(model: Any) -> dict[str, Any] | None:
        """Render the model config safely for state attributes."""
        if model is None:
            return None
        if is_dataclass(model):
            return asdict(model)
        if isinstance(model, dict):
            return dict(model)
        return {"value": model}
