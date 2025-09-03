# hass-handball.net

[![Static Badge](https://img.shields.io/badge/HACS-Custom-41BDF5?style=for-the-badge&logo=homeassistantcommunitystore&logoColor=white)](https://github.com/hacs/integration)
![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/miggi92/hass-handball.net/total?style=for-the-badge)
![GitHub Release](https://img.shields.io/github/v/release/miggi92/hass-handball.net?style=for-the-badge)
![GitHub License](https://img.shields.io/github/license/miggi92/hass-handball.net?style=for-the-badge)
![GitHub Repo stars](https://img.shields.io/github/stars/miggi92/hass-handball.net?style=for-the-badge)

> [Handball.net](https://handball.net) Home Assistant Custom Component

## Installation

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=miggi92&repository=hass-handball.net&category=Integration)

### HACS (recommended)

1. Open HACS
2. add this repository as a custom repository
3. search for "Handball.net" in the HACS store
4. install the integration
5. restart Home Assistant

### Manual

Copy the `custom_components/handballnet` folder to your Home Assistant `custom_components` folder. Then restart Home Assistant.


## Configuration

1. Open the Home Assistant UI
2. Go to `Configuration` > `Integrations`
3. Click on `+ Add Integration`
4. Search for `Handball.net`
5. Enter the team ID of your team (e.g. `id.12345` for `https://handball.net/mannschaften/id.12345`)
6. Click on `Submit`

## Example

<img src="https://github.com/miggi92/hass-handball.net/blob/main/assets/integration_example.png" width="500" alt="Integration Example" />
<img src="https://github.com/miggi92/hass-handball.net/blob/main/assets/calendar_example.png" width="500" alt="Calendar Example" />

## Features

- Fetches team information from [Handball.net](https://handball.net)
- Creates sensors for home and away games
- Creates calendar events for games
- Supports multiple teams

## Lovelace / Dashboard

### Tournament

```yaml
type: markdown
content: |
  {% set sensors = states.sensor
     | selectattr('entity_id','search','^sensor\\.daikin_hbl_platz_\\d+$')
     | map(attribute='entity_id')
     | map('regex_replace','^sensor\\.daikin_hbl_platz_(\\d+)$','\\1')
     | map('int')
     | list
     | sort %}
  | Platz | Logo | Verein | Punkte |
  | --- |:---:|:---:| ---:|
  {%- for p in sensors %}
  {%- set eid = 'sensor.daikin_hbl_platz_' ~ p %}
  {%- set s = states(eid) %}
  {%- set pic = state_attr(eid, 'entity_picture') %}
  {%- set points = state_attr(eid, 'points') %}
  | {{ p }}. | <img src="{{ pic }}" height="20"> | {{ s }} | {{ points }} |
  {%- endfor %}
title: HBL
```

## Sponsors

![Sponsors](https://github.com/miggi92/static/blob/master/sponsors.svg)
