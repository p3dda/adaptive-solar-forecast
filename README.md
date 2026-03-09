# Adaptive Solar Forecast MVP

This repository contains a first custom component scaffold for Home Assistant:

- domain: `adaptive_solar_forecast`
- type: config-entry based custom integration
- goal: post-process an existing solar forecast with a site-specific shading model

## What it does

The MVP assumes you already have forecast sensors that expose Home Assistant style forecast attributes such as:

- `watts`
- `wh_period`

It then:

1. computes sun azimuth and elevation for each forecast timestamp,
2. applies a morning azimuth-based damping curve,
3. applies an afternoon elevation-based damping curve,
4. exposes corrected sensor entities.

## Entities

The integration currently creates:

- adjusted energy today
- adjusted energy tomorrow
- current shading factor
- adjusted peak power today

The energy sensors expose the corrected `watts` and `wh_period` as attributes.

## Install

Copy `custom_components/adaptive_solar_forecast` into your Home Assistant config directory and restart Home Assistant.

Then add the integration in `Settings -> Devices & Services`.

## Current limitations

- no learning or calibration yet
- no Recorder or InfluxDB training input yet
- tuned for forecast sensors with `watts` / `wh_period` attributes
- deterministic model only

## Planned next steps

- options flow validation and constraints
- learned seasonal coefficients
- Recorder and InfluxDB training backend
- confidence score based on historical forecast error
