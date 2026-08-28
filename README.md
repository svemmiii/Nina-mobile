# NINA Mobile for Home Assistant

Unofficial Home Assistant custom integration that makes NINA warnings follow a GPS-based `device_tracker`.

> **Important:** This project is not an official BBK/NINA integration and is not affiliated with the Bundesamt für Bevölkerungsschutz und Katastrophenhilfe.

## What it does

NINA Mobile combines three pieces:

1. A Home Assistant `device_tracker` provides `latitude` and `longitude`.
2. The public BKG VG250 WFS is used to determine the current German district (Kreis) and its ARS.
3. The NINA data source is queried through `pynina`, using the same current library version as the Home Assistant Core NINA integration at the time of this release.

The result behaves like a moving NINA region for a camper, car or other mobile Home Assistant installation.

## Update behaviour

- NINA warnings are polled every **5 minutes**.
- The coordinator uses `always_update=False`: if region and warning-slot contents are unchanged, Home Assistant entities are **not written again just because a poll happened**.
- The integration listens to GPS tracker changes independently of that interval.
- After the current district polygon has been loaded, GPS movement **inside that polygon causes no region lookup and no warning refresh**.
- When the GPS point leaves the cached district polygon, the new district is resolved and NINA is refreshed immediately.
- NINA Mobile does **not** send notifications itself.

### Stable warning slots

Warning entities use fixed slots such as:

- `binary_sensor.nina_mobile_warnung_1`
- `binary_sensor.nina_mobile_warnung_2`
- ...

A warning ID stays in the same slot for as long as possible. A normal 5-minute refresh therefore does not deliberately reshuffle existing warnings. A new warning is placed into a free slot; a removed warning frees its slot.

This makes the integration easier to consume from automations and other integrations.

## Entities

For every configured slot, NINA Mobile creates one safety binary sensor containing the complete warning as attributes, including:

- `warning_id` and the NINA-compatible alias `id`
- `headline`
- `description`
- `sender`
- `severity`
- `recommended_actions`
- `affected_areas`
- `more_info_url` and the NINA-compatible alias `web`
- `sent`
- `start`
- `expires`
- `ars`
- `region`

It also creates diagnostic sensors similar to the standard NINA integration for headline, sender, severity, affected areas, URL and timestamps.

A diagnostic `Aktuelle Warnregion` sensor shows the district currently selected from GPS and exposes the ARS and GPS status as attributes.

## GPS requirements

The selected entity must be a `device_tracker` with these attributes:

```yaml
latitude: 50.1234
longitude: 7.1234
```

The GPS source can be an ESP32, Raspberry Pi, Home Assistant Companion App, MQTT tracker or anything else that ultimately creates such a `device_tracker`.

NINA Mobile does not control the GPS update interval. The tracker can therefore implement its own adaptive update logic based on movement or speed.

## Installation through HACS as a custom repository

1. Create a public GitHub repository, for example `nina-mobile`.
2. Upload the complete contents of this repository.
3. In HACS, add the GitHub repository as a **custom repository** of type **Integration**.
4. Install **NINA Mobile**.
5. Restart Home Assistant.
6. Go to **Settings → Devices & services → Add integration → NINA Mobile**.
7. Select the GPS `device_tracker` and the desired number of warning slots.

Recommended GitHub repository metadata:

- Description: `GPS-following NINA warning integration for Home Assistant`
- Topics: `home-assistant`, `hacs`, `nina`, `bbk`, `warnings`, `gps`, `device-tracker`, `germany`
- Issues: enabled

## Manual installation

Copy:

```text
custom_components/nina_mobile/
```

into:

```text
/config/custom_components/nina_mobile/
```

and restart Home Assistant.

## Behaviour when GPS is unavailable

If the tracker temporarily stops providing coordinates, NINA Mobile keeps the last successfully resolved district and continues polling warnings for it. It does not immediately clear an active warning simply because GPS disappeared for a moment.

If a valid GPS point is resolved outside Germany, the mobile region is cleared and the warning slots turn off.

## Known limitations in v0.1.0

- The integration follows the **district/ARS model** used by the Home Assistant NINA integration. It does not yet test the GPS point against each individual NINA warning polygon.
- Near an administrative boundary, inaccurate GPS positions can make the selected district switch back and forth. Boundary hysteresis can be added later.
- The public BKG VG250 WFS product page currently lists its administrative data as **01.01.2025**, while a newer downloadable VG250 dataset exists. This first version deliberately uses the WFS because it avoids bundling a large Germany-wide geometry file.
- This is an initial implementation and should be tested with real Home Assistant/NINA data before being treated as safety-critical.

## Data sources and attribution

### NINA / BBK

Warning data is retrieved from the public NINA warning infrastructure (`warnung.bund.de`) through the `pynina` Python package.

### BKG administrative districts

District geometry and ARS information are requested from the public BKG VG250 WFS:

`https://sgx.geodatenzentrum.de/wfs_vg250`

Attribution for the currently published WFS dataset:

© GeoBasis-DE / BKG 2025, dl-de/by-2-0. Data sources: BKG / German surveying authorities as documented by the BKG.

## License

The integration source code is released under the MIT License. External warning and geodata remain subject to the terms of their respective providers.
