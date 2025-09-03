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

## Screenshots

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
### Team

#### Next Match

Using [Button-Card](https://github.com/custom-cards/button-card)

```yaml
button_card_templates:
  handballnet_next_game_card:
    show_name: false
    show_state: false
    show_icon: false
    styles:
      card:
        - padding: 12px
        - font-size: 14px
        - text-align: center
        - border-radius: 12px
        - box-shadow: 0 2px 6px rgba(0,0,0,0.3)
      grid:
        - grid-template-areas: |
            "home vs away"
            "homeName date awayName"
            "homeRecord info awayRecord"
            "bottom bottom bottom"
        - grid-template-columns: 1fr auto 1fr
        - grid-template-rows: auto auto auto auto
    custom_fields:
      home: |
        [[[
          const m = states[entity.entity_id].attributes.upcoming_matches[0];
          return `<img src="${m.homeTeam.logo}" height="50">`;
        ]]]
      away: |
        [[[
          const m = states[entity.entity_id].attributes.upcoming_matches[0];
          return `<img src="${m.awayTeam.logo}" height="50">`;
        ]]]
      vs: |
        🆚
      homeName: |
        [[[
          const m = states[entity.entity_id].attributes.upcoming_matches[0];
          return `<b>${m.homeTeam.name}</b>`;
        ]]]
      awayName: |
        [[[
          const m = states[entity.entity_id].attributes.upcoming_matches[0];
          return `<b>${m.awayTeam.name}</b>`;
        ]]]
      date: |
        [[[
          const m = states[entity.entity_id].attributes.next_match;
          const ts = new Date(m.starts_at_local);
          return ts.toLocaleDateString('de-DE', { weekday: 'long', day: '2-digit', month: '2-digit', year:'numeric' })
            + '<br>' + ts.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
        ]]]
      info: |
        [[[
          const m = states[entity.entity_id].attributes.next_match;
          return `📍 ${m.field}`;
        ]]]
      bottom: |
        [[[
          const m = states[entity.entity_id].attributes.upcoming_matches[0];
          return `🏆 ${m.tournament.name}`;
        ]]]
```

```yaml
type: custom:button-card
template: handballnet_next_game_card
entity: sensor.thw_kiel_alle_spiele
```

## Sponsors

![Sponsors](https://github.com/miggi92/static/blob/master/sponsors.svg)
