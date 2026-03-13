# Adaptive Solar Forecast

`adaptive_solar_forecast` is a Home Assistant custom integration that post-processes an existing solar forecast with a site-specific shading model.

[![Validate with HACS](https://img.shields.io/github/actions/workflow/status/p3dda/adaptive-solar-forecast/validate.yaml?branch=main&label=HACS)](https://github.com/p3dda/adaptive-solar-forecast/actions/workflows/validate.yaml)
[![Validate with Hassfest](https://img.shields.io/github/actions/workflow/status/p3dda/adaptive-solar-forecast/hassfest.yaml?branch=main&label=Hassfest)](https://github.com/p3dda/adaptive-solar-forecast/actions/workflows/hassfest.yaml)
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=p3dda&repository=adaptive-solar-forecast&category=integration)

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

## Validation

The repository is prepared for two GitHub-based validation paths:
- `HACS` validation for repository structure and packaging
- `Hassfest` validation for Home Assistant custom integration metadata

Included workflows:
- `.github/workflows/validate.yaml`
- `.github/workflows/hassfest.yaml`

Current caveats:
- GitHub repository description and topics should be set in the GitHub UI for a cleaner HACS validation result

## Install smoke test

The intended installation smoke test is:
1. Install via HACS custom repository or copy the integration manually.
2. Restart Home Assistant.
3. Add `Adaptive Solar Forecast` in the integrations UI.
4. Select forecast sensor(s) and `sun.sun`.
5. Confirm the new adjusted sensors are created and expose corrected `watts` and `wh_period`.

Expected MVP behavior:
- corrected energy sensors appear after setup
- `Current Shading Factor` changes during the day
- corrected forecast values are lower than the source forecast in shaded windows

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
- replace placeholder brand assets with final artwork

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

Note: `ModelConfig` in `model.py` intentionally uses a non-slotted dataclass to keep attribute serialization stable.

## License

This project is licensed under Apache-2.0. See [`LICENSE`](LICENSE).
