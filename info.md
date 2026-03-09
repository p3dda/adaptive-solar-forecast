# Adaptive Solar Forecast

Adaptive Solar Forecast is a Home Assistant custom integration that corrects an existing PV forecast with a local shading model.

It is intended for installations where the base forecast is broadly useful, but recurring local effects such as:
- neighboring buildings in the morning
- trees or buildings in the afternoon
- low-sun-angle losses across seasons

cause systematic forecast errors.

The current MVP focuses on:
- post-processing an existing forecast source
- morning azimuth damping
- afternoon elevation damping
- configuration through the Home Assistant UI

Planned future work includes:
- calibration from Recorder or InfluxDB
- seasonal adaptation
- optional machine-learning assisted correction
