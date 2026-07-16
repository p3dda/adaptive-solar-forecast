"""Constants for Adaptive Solar Forecast."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "adaptive_solar_forecast"
NAME: Final = "Adaptive Solar Forecast"

CONF_FORECAST_TODAY_ENTITY: Final = "forecast_today_entity"
CONF_FORECAST_TOMORROW_ENTITY: Final = "forecast_tomorrow_entity"
CONF_SUN_ENTITY: Final = "sun_entity"
CONF_NAME: Final = "name"
CONF_UPDATE_INTERVAL: Final = "update_interval"

CONF_MORNING_FREE_AZIMUTH: Final = "morning_free_azimuth"
CONF_MORNING_SHADE_START_AZIMUTH: Final = "morning_shade_start_azimuth"
CONF_MORNING_SHADE_END_AZIMUTH: Final = "morning_shade_end_azimuth"
CONF_MORNING_RECOVER_AZIMUTH: Final = "morning_recover_azimuth"
CONF_MORNING_DEEP_FACTOR: Final = "morning_deep_factor"

CONF_AFTERNOON_HIGH_ELEVATION: Final = "afternoon_high_elevation"
CONF_AFTERNOON_MID_ELEVATION: Final = "afternoon_mid_elevation"
CONF_AFTERNOON_LOW_ELEVATION: Final = "afternoon_low_elevation"
CONF_AFTERNOON_DEEP_ELEVATION: Final = "afternoon_deep_elevation"
CONF_AFTERNOON_END_ELEVATION: Final = "afternoon_end_elevation"
CONF_AFTERNOON_MID_FACTOR: Final = "afternoon_mid_factor"
CONF_AFTERNOON_LOW_FACTOR: Final = "afternoon_low_factor"
CONF_AFTERNOON_DEEP_FACTOR: Final = "afternoon_deep_factor"
CONF_AFTERNOON_END_FACTOR: Final = "afternoon_end_factor"
CONF_AFTERNOON_HORIZON_FACTOR: Final = "afternoon_horizon_factor"
CONF_AFTER_SOLAR_NOON_ONLY: Final = "after_solar_noon_only"

CONF_ACTUAL_PRODUCTION_ENTITY: Final = "actual_production_entity"
CONF_CALIBRATION_CLIP_WATTS: Final = "calibration_clip_watts"
CONF_CALIBRATION_DAYS: Final = "calibration_days"
CONF_BATTERY_FULL_ENTITY: Final = "battery_full_entity"
CONF_BATTERY_FULL_THRESHOLD: Final = "battery_full_threshold"

SERVICE_CALIBRATE: Final = "calibrate"

DEFAULT_NAME: Final = "Adaptive Solar Forecast"
DEFAULT_SUN_ENTITY: Final = "sun.sun"
DEFAULT_UPDATE_INTERVAL = 30

DEFAULT_MORNING_FREE_AZIMUTH = 105.0
DEFAULT_MORNING_SHADE_START_AZIMUTH = 120.0
DEFAULT_MORNING_SHADE_END_AZIMUTH = 135.0
DEFAULT_MORNING_RECOVER_AZIMUTH = 150.0
DEFAULT_MORNING_DEEP_FACTOR = 0.35

DEFAULT_AFTERNOON_HIGH_ELEVATION = 30.0
DEFAULT_AFTERNOON_MID_ELEVATION = 24.0
DEFAULT_AFTERNOON_LOW_ELEVATION = 18.0
DEFAULT_AFTERNOON_DEEP_ELEVATION = 12.0
DEFAULT_AFTERNOON_END_ELEVATION = 6.0
DEFAULT_AFTERNOON_MID_FACTOR = 0.80
DEFAULT_AFTERNOON_LOW_FACTOR = 0.55
DEFAULT_AFTERNOON_DEEP_FACTOR = 0.30
DEFAULT_AFTERNOON_END_FACTOR = 0.12
DEFAULT_AFTERNOON_HORIZON_FACTOR = 0.03
DEFAULT_AFTER_SOLAR_NOON_ONLY = True

# Curtailment guard: a Balkonkraftwerk inverter clamps output (commonly to
# 800 W) once the battery is full, so those samples reflect a legal/hardware
# cap rather than shading and must be excluded from calibration.
DEFAULT_CALIBRATION_CLIP_WATTS = 800.0
DEFAULT_CALIBRATION_DAYS = 30
DEFAULT_BATTERY_FULL_THRESHOLD = 100.0

# Calibration sampling guards.
CALIBRATION_MIN_EXPECTED_WATTS = 20.0  # ignore near-dawn/dusk noise
CALIBRATION_CLIP_MARGIN = 0.98  # treat >= 98% of the clip as curtailed
CALIBRATION_MAX_FACTOR = 1.0  # shading can only reduce output
CALIBRATION_MIN_BUCKET_SAMPLES = 30  # below this, a suggestion is low-confidence
CALIBRATION_MAX_SPREAD = 0.25  # IQR above this means the bucket is too noisy to trust

# Reference normalization: samples the model treats as essentially unshaded are
# used to measure forecast bias, so shading factors are expressed relative to the
# observed unshaded baseline rather than the raw (possibly biased) forecast.
CALIBRATION_REFERENCE_MIN_MODEL_FACTOR = 0.95
CALIBRATION_REFERENCE_MIN_SAMPLES = 20

DEFAULT_SCAN_INTERVAL = timedelta(minutes=DEFAULT_UPDATE_INTERVAL)
