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
CONF_BATTERY_POWER_ENTITY: Final = "battery_power_entity"

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

# Curtailment guard. When the battery is full, the only path for PV is the AC
# output (commonly capped at 800 W), so raw PV is clamped to that cap and hides
# the true generation. Such samples are excluded. The clip value is the AC cap,
# used together with the battery-power signal: raw PV at the cap while the
# battery is not absorbing means curtailment. Raw PV above the cap while the
# battery IS charging is genuine (uncurtailed) and kept.
DEFAULT_CALIBRATION_CLIP_WATTS = 800.0
DEFAULT_CALIBRATION_DAYS = 30
DEFAULT_BATTERY_FULL_THRESHOLD = 100.0

# Calibration sampling guards.
CALIBRATION_MIN_EXPECTED_WATTS = 20.0  # absolute floor: ignore near-dawn/dusk noise
# Relative floor: also require the expected power to be at least this fraction of
# the forecast day's peak. Near the horizon the forecast is tiny and unreliable,
# so actual/forecast explodes into noise; this scales the cutoff with system size
# instead of a single absolute watt value.
CALIBRATION_MIN_EXPECTED_PEAK_FRACTION = 0.05
CALIBRATION_CLIP_MARGIN = 0.98  # treat >= 98% of the AC cap as "at the cap"
CALIBRATION_BATTERY_IDLE_WATTS = 50.0  # |battery power| below this = not absorbing
CALIBRATION_MAX_FACTOR = 1.0  # shading can only reduce output
CALIBRATION_MIN_BUCKET_SAMPLES = 30  # below this, a suggestion is low-confidence
CALIBRATION_MAX_SPREAD = 0.25  # IQR above this means the bucket is too noisy to trust
# If most of a band's samples were curtailed/battery-excluded, its clear-sky
# peaks are missing and the envelope under-reads -- so it cannot be trusted even
# if the surviving (cloudy) samples happen to agree. High-sun afternoon bands on
# a battery system are the typical victims.
CALIBRATION_MAX_CURTAILMENT_RATIO = 0.35

# Reference normalization: samples the model treats as essentially unshaded are
# used to measure forecast bias, so shading factors are expressed relative to the
# observed unshaded baseline rather than the raw (possibly biased) forecast.
CALIBRATION_REFERENCE_MIN_MODEL_FACTOR = 0.95
CALIBRATION_REFERENCE_MIN_SAMPLES = 20

# Upper-envelope estimator: clouds and battery curtailment can only push actual
# production *below* the true shading ceiling, so the shading factor is estimated
# from a high percentile of actual/expected per bucket rather than the median.
CALIBRATION_ENVELOPE_PERCENTILE = 0.85

DEFAULT_SCAN_INTERVAL = timedelta(minutes=DEFAULT_UPDATE_INTERVAL)
