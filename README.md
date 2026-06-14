# Air Quality Metrics for Home Assistant

[![GitHub Release][releases-shield]][releases]
![Project Stage][project-stage-shield]
[![License][license-shield]](LICENSE.md)

![Supports aarch64 Architecture][aarch64-shield]
![Supports amd64 Architecture][amd64-shield]

[![Github Actions][github-actions-shield]][github-actions]
![Project Maintenance][maintenance-shield]
[![GitHub Activity][commits-shield]][commits]

A Home Assistant custom component that calculates precise EPA Air Quality Index
(AQI and NowCast) and Indoor Air Quality (IAQI) values from raw sensor data.

## Features

Produces air quality metrics for either indoor or outdoor sensors, for a variety
of pollutant sensors.

- Indoor Sensors
  - IAQI: ATMO produced this scale and formula as a way to produce a rating similar to AQI, but for indoor spaces.
    - https://atmotube.com/blog/indoor-air-quality-index-iaqi
- Outdoor Sensors
  - EPA NowCast AQI: This is what most people think of when they hear "AQI."
    This "real time" metric still requires valid data from 2 out of the previous
    3 hours, but will produce a reading on the AQI scale much better suited to
    people wanting to know what the air quality is like "right now," whether the
    concern is pollen, smog, or wildire smoke.
    - https://en.wikipedia.org/wiki/NowCast_(air_quality_index)
  - EPA AQI: Intended as a general air quality score spread across an entire day
    (midnight to midnight), the formula used by this integration takes a more
    liberal approach and looks at 24 hour windows to produce a smoother value
    curve.
    - https://en.wikipedia.org/wiki/Air_quality_index#United_States
    - https://en.wikipedia.org/wiki/Air_quality_index#Computing_the_AQI

Future metrics to be implemented [RSN](https://en.wiktionary.org/wiki/real_soon_now):

  - CAQI: This is the European equivalent to the EPA's AQI. The scale and
    formulas are different.
    - https://en.wikipedia.org/wiki/Air_quality_index#CAQI
  - RESET: This group produces standards and programs related to indoor
    commercial space. They have published information about air quality, but I
    haven't yet had time to see if there is anything that can be added to this
    integration.
    - https://reset.build/standard/air


## How can you help?

- Translations! I might use AI to help with some of the code but I don't trust
  translations to be accurate within the contexts that they need to be.
- I have some older AirGradient hardware but nothing with sensors for some of
  the more exotic gasses/particles. I'd love some feedback from anyone who does,
  or recommendations for what hardware I should get so I can run my own tests.
- Know anyone on the Home Assistant core team who can provide insight about
  adding new device classes? It would be great to support:
  - VOC Index like from https://esphome.io/components/sensor/sgp4x/
  - NOx Index like from https://esphome.io/components/sensor/sgp4x/
  - Formaldehyde like from https://esphome.io/components/sensor/sfa30/
    or https://esphome.io/components/sensor/sm300d2/

## Installation

### Method 1: HACS (Recommended)

1. Open **HACS** in your Home Assistant panel.
2. Click the three dots in the top-right corner and select **Custom repositories**.
3. Paste your repository URL: `https://github.com/ex-nerd/ha-air-quality-metrics`
4. Select **Integration** as the category and click **Add**.
5. Find **Air Quality** in the HACS store, click **Download**, and restart Home Assistant.

### Method 2: Manual Installation

1. Download the latest release source code.
2. Copy the contents of the `custom_components/air_quality_metrics` folder into your Home Assistant's `config/custom_components/air_quality_metrics` directory.
3. Restart Home Assistant.

## Configuration

Once installed, you can configure the integration directly through the Home Assistant user interface:

1. Navigate to **Settings** -> **Devices & Services**.
2. Click **+ Add Integration** in the bottom right corner.
3. Search for **Air Quality** and follow the on-screen configuration flow.

## Bug Reports & Feedback

If you encounter issues or have feature requests, please log them in our official [Issue Tracker](https://github.com/ex-nerd/ha-air-quality-metrics/issues).

## Code Owners

- [@ex-nerd](https://github.com/ex-nerd)

## Air Quality Resources

- https://document.airnow.gov/technical-assistance-document-for-the-reporting-of-daily-air-quailty.pdf

[releases-shield]: https://img.shields.io/github/v/release/ex-nerd/ha-air-quality-metrics?style=flat-square
[releases]: https://github.com/ex-nerd/ha-air-quality-metrics/releases
[project-stage-shield]: https://img.shields.io/badge/project%20stage-production-brightgreen.svg?style=flat-square
[license-shield]: https://img.shields.io/github/license/ex-nerd/ha-air-quality-metrics?style=flat-square
[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green?style=flat-square
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green?style=flat-square
[github-actions-shield]: https://img.shields.io/github/actions/workflow/status/ex-nerd/ha-air-quality-metrics/tests.yml?branch=main&style=flat-square
[github-actions]: https://github.com/ex-nerd/ha-air-quality-metrics/actions
[maintenance-shield]: https://img.shields.io/badge/maintained%3F-yes-green.svg?style=flat-square
[commits-shield]: https://img.shields.io/github/commit-activity/m/ex-nerd/ha-air-quality-metrics?style=flat-square
[commits]: https://github.com/ex-nerd/ha-air-quality-metrics/graphs/commit-activity