# hass-handball.net

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)
![GitHub Release](https://img.shields.io/github/v/release/miggi92/hass-handball.net?style=for-the-badge)
![GitHub License](https://img.shields.io/github/license/miggi92/hass-handball.net?style=for-the-badge)
![GitHub Repo stars](https://img.shields.io/github/stars/miggi92/hass-handball.net?style=for-the-badge)

> [Handball.net](https://handball.net) Home Assistant Custom Component

## Installation

### HACS (recommended)

1. Open HACS
2. add this repository as a custom repository
3. search for "Handball.net" in the HACS store
4. install the integration
5. restart Home Assistant

### Manual

Copy the `custom_components/handball_net` folder to your Home Assistant `custom_components` folder. Then restart Home Assistant.


## Configuration

1. Open the Home Assistant UI
2. Go to `Configuration` > `Integrations`
3. Click on `+ Add Integration`
4. Search for `Handball.net`
5. Enter the team ID of your team (e.g. `12345` for `https://handball.net/team/12345`)
6. Click on `Submit`

## Example

![Integration Example](assets/integration_example.png)
![Calendar Example](assets/calendar_example.png)

## Features

- Fetches team information from [Handball.net](https://handball.net)
- Creates sensors for home and away games
- Creates calendar events for games
- Supports multiple teams
