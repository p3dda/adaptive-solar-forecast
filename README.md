# Adaptive Solar Forecast

`adaptive_solar_forecast` is a Home Assistant custom integration that post-processes an existing solar forecast with a site-specific shading model.

The initial target is a common real-world setup:
- the base forecast is broadly correct
- the installation has recurring local shading
- the biggest forecast errors come from repeatable morning and afternoon losses

Instead of replacing the upstream forecast source, this integration adjusts it using sun position and a tunable shading model.

## Status

This project is in an early MVP state.

What already exists:
- config-entry based custom integration
- support for forecast entities with `watts` and/or `wh_period` attributes
- deterministic morning azimuth damping
- deterministic afternoon elevation damping
- corrected forecast sensors for today and tomorrow

What does not exist yet:
- automatic calibration from Recorder or InfluxDB
- adaptive or ML-based learning
- long-term confidence scoring
- production hardening and broad compatibility testing

## How it works

The integration reads an existing forecast sensor and applies a correction factor for each forecast timestamp.

Current inputs:
- a forecast sensor for today
- optionally a forecast sensor for tomorrow
- a sun entity, typically `sun.sun`
- Home Assistant location data for timestamp-based sun position calculation

Current model:
1. Morning correction based on azimuth
2. Afternoon correction based on elevation
3. A combined factor applied to forecast power and energy buckets

This makes it useful for installations where:
- a neighboring building blocks part of the morning sun
- trees, chimneys, or buildings create recurring afternoon losses
- the error pattern is systematic rather than random

## Created entities

The MVP currently creates these sensors:
- `Adjusted Energy Today`
- `Adjusted Energy Tomorrow`
- `Current Shading Factor`
- `Adjusted Peak Power Today`

The energy sensors also expose:
- adjusted `watts`
- adjusted `wh_period`
- mean applied model factor
- source forecast entity

## Installation

### HACS

HACS metadata is included in this repository.

Once the repository is public, add it to HACS as a custom repository of type `Integration`, then install `Adaptive Solar Forecast`.

### Manual

Copy [`custom_components/adaptive_solar_forecast`](custom_components/adaptive_solar_forecast) into your Home Assistant configuration directory under:

```text
config/custom_components/adaptive_solar_forecast
```

Then restart Home Assistant and add the integration in:

`Settings -> Devices & Services -> Add Integration`

## Configuration

The config flow currently asks for:
- integration name
- forecast sensor for today
- optional forecast sensor for tomorrow
- sun entity
- update interval

Advanced options expose the current rule-based shading model:
- morning azimuth thresholds
- morning deep-shadow factor
- afternoon elevation thresholds
- afternoon damping factors

## Compatibility assumptions

The current MVP expects forecast sensors that expose Home Assistant-style structured forecast attributes such as:
- `watts`
- `wh_period`

The project was initially designed around forecast sensors like `energy_production_today` and `energy_production_tomorrow`, but it is intended to work with any forecast source that follows the same attribute pattern.

## Roadmap

Near-term:
- validate config values and threshold ordering
- make the sensor model and attributes more robust
- add diagnostics and better error messages

Next phase:
- calibrate the model from historical Recorder data
- support InfluxDB-backed training data
- derive seasonal coefficients automatically

Later:
- adaptive parameter learning
- optional ML-assisted correction layer
- confidence and forecast quality scoring

## Development

Repository:
- GitHub: `https://github.com/p3dda/adaptive-solar-forecast`
- Home Assistant domain: `adaptive_solar_forecast`

Current structure:
- [`custom_components/adaptive_solar_forecast/config_flow.py`](custom_components/adaptive_solar_forecast/config_flow.py)
- [`custom_components/adaptive_solar_forecast/coordinator.py`](custom_components/adaptive_solar_forecast/coordinator.py)
- [`custom_components/adaptive_solar_forecast/model.py`](custom_components/adaptive_solar_forecast/model.py)
- [`custom_components/adaptive_solar_forecast/sensor.py`](custom_components/adaptive_solar_forecast/sensor.py)

## License

This project is licensed under Apache-2.0. See [`LICENSE`](LICENSE).
