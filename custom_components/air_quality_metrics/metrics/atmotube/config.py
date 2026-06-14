"""
See numbers posted here: https://atmotube.com/blog/indoor-air-quality-index-iaqi
"""

from typing import Final

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    CONCENTRATION_PARTS_PER_MILLION,
)

from custom_components.air_quality_metrics.metrics.atmotube.types import (
    IAQIBreakpoint,
    IAQICategory,
    IAQICategoryGrouping,
    IAQISensorConfig,
    IAQISensorType,
)

# TODO: replace with frozendict once Home Assistant minimum python>=3.15
IAQI_CATEGORY: Final[IAQICategoryGrouping] = {
    "good": IAQICategory(
        category="good",
        color="#56ceb5",
        idx_low=100,
        idx_high=81,
    ),
    "moderate": IAQICategory(
        category="moderate",
        color="#b0c160",
        idx_low=80,
        idx_high=61,
    ),
    "polluted": IAQICategory(
        category="polluted",
        color="#fcb35d",
        idx_low=60,
        idx_high=41,
    ),
    "very_polluted": IAQICategory(
        category="very_polluted",
        color="#ea6445",
        idx_low=40,
        idx_high=21,
    ),
    "severely_polluted": IAQICategory(
        category="severely_polluted",
        color="#d32758",
        idx_low=20,
        idx_high=0,
    ),
}
# Global constants mapping ATMO thresholds, last verified 2026-06-14
# See: https://atmotube.com/blog/indoor-air-quality-index-iaqi
IAQI_CONFIGS: dict[IAQISensorType, IAQISensorConfig[IAQI_CATEGORY]] = {
    # There isn't a device class for VOC Index, so we'll need some work to support this. See README.
    # SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS: IAQISensorConfig(
    #     unit=index (but what index is atmotube using?)
    #     precision=0,
    #     breakpoints=[
    #         IAQIBreakpoint(1, 199, IAQI_CATEGORY["good"]),
    #         IAQIBreakpoint(200, 249, IAQI_CATEGORY["moderate"]),
    #         IAQIBreakpoint(250, 349, IAQI_CATEGORY["polluted"]),
    #         IAQIBreakpoint(350, 399, IAQI_CATEGORY["very_polluted"]),
    #         IAQIBreakpoint(400, 500, IAQI_CATEGORY["severely_polluted"]),
    #     ],
    # ),
    # There isn't a device class for NOx Index, so we'll need some work to support this. See README.
    # SensorDeviceClass.NOx: IAQISensorConfig(
    #     unit=index
    #     precision=0,
    #     breakpoints=[
    #         IAQIBreakpoint(1, 49, IAQI_CATEGORY["good"]),
    #         IAQIBreakpoint(50, 99, IAQI_CATEGORY["moderate"]),
    #         IAQIBreakpoint(100, 299, IAQI_CATEGORY["polluted"]),
    #         IAQIBreakpoint(300, 349, IAQI_CATEGORY["very_polluted"]),
    #         IAQIBreakpoint(350, 500, IAQI_CATEGORY["severely_polluted"]),
    #     ],
    # ),
    # Home Assistant doesn't seem to have a formaldehyde device class. See README.
    # SensorDeviceClass.CH2O (or HCH0? ... formaldehyde): IAQISensorConfig(
    #     unit=CONCENTRATION_PARTS_PER_MILLION
    #     precision=2,
    #     breakpoints=[
    #         IAQIBreakpoint(0.00, 0.05, IAQI_CATEGORY["good"]),
    #         IAQIBreakpoint(0.06, 0.10, IAQI_CATEGORY["moderate"]),
    #         IAQIBreakpoint(0.11, 0.30, IAQI_CATEGORY["polluted"]),
    #         IAQIBreakpoint(0.31, 0.75, IAQI_CATEGORY["very_polluted"]),
    #         IAQIBreakpoint(0.76, 100, IAQI_CATEGORY["severely_polluted"]),
    #     ],
    # ),
    SensorDeviceClass.CO: IAQISensorConfig(
        unit=CONCENTRATION_PARTS_PER_MILLION,
        precision=1,
        breakpoints=[
            IAQIBreakpoint(0, 1.7, IAQI_CATEGORY["good"]),
            IAQIBreakpoint(1.8, 8.7, IAQI_CATEGORY["moderate"]),
            IAQIBreakpoint(8.8, 10.0, IAQI_CATEGORY["polluted"]),
            IAQIBreakpoint(10.1, 15.0, IAQI_CATEGORY["very_polluted"]),
            IAQIBreakpoint(15.1, 30.0, IAQI_CATEGORY["severely_polluted"]),
        ],
    ),
    SensorDeviceClass.CO2: IAQISensorConfig(
        unit=CONCENTRATION_PARTS_PER_MILLION,
        precision=0,
        breakpoints=[
            IAQIBreakpoint(400, 599, IAQI_CATEGORY["good"]),
            IAQIBreakpoint(600, 999, IAQI_CATEGORY["moderate"]),
            IAQIBreakpoint(1000, 1499, IAQI_CATEGORY["polluted"]),
            IAQIBreakpoint(1500, 2499, IAQI_CATEGORY["very_polluted"]),
            IAQIBreakpoint(2500, 4000, IAQI_CATEGORY["severely_polluted"]),
        ],
    ),
    SensorDeviceClass.OZONE: IAQISensorConfig(
        unit=CONCENTRATION_PARTS_PER_MILLION,
        precision=3,
        breakpoints=[
            IAQIBreakpoint(0.000, 0.025, IAQI_CATEGORY["good"]),
            IAQIBreakpoint(0.026, 0.060, IAQI_CATEGORY["moderate"]),
            IAQIBreakpoint(0.061, 0.075, IAQI_CATEGORY["polluted"]),
            IAQIBreakpoint(0.076, 0.100, IAQI_CATEGORY["very_polluted"]),
            IAQIBreakpoint(0.101, 0.300, IAQI_CATEGORY["severely_polluted"]),
        ],
    ),
    SensorDeviceClass.PM1: IAQISensorConfig(
        unit=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        precision=0,
        breakpoints=[
            IAQIBreakpoint(0, 14, IAQI_CATEGORY["good"]),
            IAQIBreakpoint(15, 34, IAQI_CATEGORY["moderate"]),
            IAQIBreakpoint(35, 61, IAQI_CATEGORY["polluted"]),
            IAQIBreakpoint(62, 95, IAQI_CATEGORY["very_polluted"]),
            IAQIBreakpoint(96, 150, IAQI_CATEGORY["severely_polluted"]),
        ],
    ),
    SensorDeviceClass.PM25: IAQISensorConfig(
        unit=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        precision=0,
        breakpoints=[
            IAQIBreakpoint(0, 20, IAQI_CATEGORY["good"]),
            IAQIBreakpoint(21, 50, IAQI_CATEGORY["moderate"]),
            IAQIBreakpoint(51, 90, IAQI_CATEGORY["polluted"]),
            IAQIBreakpoint(91, 140, IAQI_CATEGORY["very_polluted"]),
            IAQIBreakpoint(141, 200, IAQI_CATEGORY["severely_polluted"]),
        ],
    ),
    SensorDeviceClass.PM10: IAQISensorConfig(
        unit=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        precision=0,
        breakpoints=[
            IAQIBreakpoint(0, 30, IAQI_CATEGORY["good"]),
            IAQIBreakpoint(31, 75, IAQI_CATEGORY["moderate"]),
            IAQIBreakpoint(76, 125, IAQI_CATEGORY["polluted"]),
            IAQIBreakpoint(126, 200, IAQI_CATEGORY["very_polluted"]),
            IAQIBreakpoint(201, 300, IAQI_CATEGORY["severely_polluted"]),
        ],
    ),
}
