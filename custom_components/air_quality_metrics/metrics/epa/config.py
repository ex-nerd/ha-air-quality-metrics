from typing import Final

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
    CONCENTRATION_PARTS_PER_BILLION,
    CONCENTRATION_PARTS_PER_MILLION,
)

from custom_components.air_quality_metrics.metrics.epa.types import (
    AQIBreakpoint,
    AQICategory,
    AQICategoryGrouping,
    AQISensorConfig,
    AQISensorType,
)

# TODO: replace with frozendict once Home Assistant minimum python>=3.15
AQI_CATEGORY: Final[AQICategoryGrouping] = {
    "good": AQICategory(
        category="good",
        color_name="green",
        color="#00e400",
        color_assist="#9eff91",
        idx_low=0,
        idx_high=50,
    ),
    "moderate": AQICategory(
        category="moderate",
        color_name="yellow",
        color="#ffff00",
        color_assist="#ffc905",
        idx_low=51,
        idx_high=100,
    ),
    "unhealthy_sensitive": AQICategory(
        category="unhealthy_sensitive",
        color_name="orange",
        color="#ff8000",
        color_assist="#ff8205",
        idx_low=101,
        idx_high=150,
    ),
    "unhealthy": AQICategory(
        category="unhealthy",
        color_name="red",
        color="#ff0000",
        color_assist="#f02200",
        idx_low=151,
        idx_high=200,
    ),
    "very_unhealthy": AQICategory(
        category="very_unhealthy",
        color_name="purple",
        color="#8f3f97",
        color_assist="#890997",
        idx_low=201,
        idx_high=300,
    ),
    "hazardous": AQICategory(
        category="hazardous",
        color_name="maroon",
        color="#7e0023",
        color_assist="#640015",
        idx_low=301,
        idx_high=500,
    ),
}


# Global constants mapping EPA thresholds, last verified 2026-06-14
# See: https://document.airnow.gov/technical-assistance-document-for-the-reporting-of-daily-air-quailty.pdf
# See: https://en.wikipedia.org/wiki/Air_quality_index#Computing_the_AQI
AQI_CONFIGS: dict[AQISensorType, AQISensorConfig] = {
    "ozone.8hour": AQISensorConfig(
        unit=CONCENTRATION_PARTS_PER_MILLION,
        precision=3,
        breakpoints=[
            AQIBreakpoint(0.000, 0.054, AQI_CATEGORY["good"]),
            AQIBreakpoint(0.055, 0.070, AQI_CATEGORY["moderate"]),
            AQIBreakpoint(0.071, 0.085, AQI_CATEGORY["unhealthy_sensitive"]),
            AQIBreakpoint(0.086, 0.105, AQI_CATEGORY["unhealthy"]),
            AQIBreakpoint(0.106, 0.200, AQI_CATEGORY["very_unhealthy"]),
            # This does not have the final breakpoint. If higher, the ozone.1hour measurement should be used
            # AQIBreakpoint(0.201, float('inf'), AQI_CATEGORY["hazardous"])),
        ],
    ),
    "ozone.1hour": AQISensorConfig(
        unit=CONCENTRATION_PARTS_PER_MILLION,
        precision=3,
        breakpoints=[
            # This does not have the first two breakpoints
            # AQIBreakpoint(0.000, 0.000, EPA_AQI_CATEGORIES["good"]),
            # AQIBreakpoint(0.000, 0.000, EPA_AQI_CATEGORIES["moderate"]),
            AQIBreakpoint(0.125, 0.164, AQI_CATEGORY["unhealthy_sensitive"]),
            AQIBreakpoint(0.165, 0.204, AQI_CATEGORY["unhealthy"]),
            AQIBreakpoint(0.205, 0.404, AQI_CATEGORY["very_unhealthy"]),
            AQIBreakpoint(0.405, 0.604, AQI_CATEGORY["hazardous"]),
        ],
    ),
    SensorDeviceClass.CO: AQISensorConfig(
        unit=CONCENTRATION_PARTS_PER_MILLION,
        precision=1,
        breakpoints=[
            AQIBreakpoint(0, 4.4, AQI_CATEGORY["good"]),
            AQIBreakpoint(4.5, 9.4, AQI_CATEGORY["moderate"]),
            AQIBreakpoint(9.5, 12.4, AQI_CATEGORY["unhealthy_sensitive"]),
            AQIBreakpoint(12.5, 15.4, AQI_CATEGORY["unhealthy"]),
            AQIBreakpoint(15.5, 30.4, AQI_CATEGORY["very_unhealthy"]),
            AQIBreakpoint(30.5, 50.4, AQI_CATEGORY["hazardous"]),
        ],
    ),
    SensorDeviceClass.SULPHUR_DIOXIDE: AQISensorConfig(
        unit=CONCENTRATION_PARTS_PER_BILLION,
        precision=0,
        breakpoints=[
            AQIBreakpoint(0, 35, AQI_CATEGORY["good"]),
            AQIBreakpoint(36, 75, AQI_CATEGORY["moderate"]),
            AQIBreakpoint(76, 185, AQI_CATEGORY["unhealthy_sensitive"]),
            AQIBreakpoint(186, 304, AQI_CATEGORY["unhealthy"]),
            AQIBreakpoint(305, 604, AQI_CATEGORY["very_unhealthy"]),
            AQIBreakpoint(605, 1004, AQI_CATEGORY["hazardous"]),
        ],
    ),
    SensorDeviceClass.NITROGEN_DIOXIDE: AQISensorConfig(
        unit=CONCENTRATION_PARTS_PER_BILLION,
        precision=0,
        breakpoints=[
            AQIBreakpoint(0, 53, AQI_CATEGORY["good"]),
            AQIBreakpoint(54, 100, AQI_CATEGORY["moderate"]),
            AQIBreakpoint(101, 360, AQI_CATEGORY["unhealthy_sensitive"]),
            AQIBreakpoint(361, 649, AQI_CATEGORY["unhealthy"]),
            AQIBreakpoint(650, 1249, AQI_CATEGORY["very_unhealthy"]),
            AQIBreakpoint(1250, 2049, AQI_CATEGORY["hazardous"]),
        ],
    ),
    SensorDeviceClass.PM25: AQISensorConfig(
        unit=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        precision=1,
        breakpoints=[
            AQIBreakpoint(0.0, 9.0, AQI_CATEGORY["good"]),
            AQIBreakpoint(9.1, 35.4, AQI_CATEGORY["moderate"]),
            AQIBreakpoint(35.5, 55.4, AQI_CATEGORY["unhealthy_sensitive"]),
            AQIBreakpoint(55.5, 125.4, AQI_CATEGORY["unhealthy"]),
            AQIBreakpoint(125.5, 225.4, AQI_CATEGORY["very_unhealthy"]),
            AQIBreakpoint(225.5, 325.4, AQI_CATEGORY["hazardous"]),
        ],
    ),
    SensorDeviceClass.PM10: AQISensorConfig(
        unit=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        precision=0,
        breakpoints=[
            AQIBreakpoint(0, 54, AQI_CATEGORY["good"]),
            AQIBreakpoint(55, 154, AQI_CATEGORY["moderate"]),
            AQIBreakpoint(155, 254, AQI_CATEGORY["unhealthy_sensitive"]),
            AQIBreakpoint(255, 354, AQI_CATEGORY["unhealthy"]),
            AQIBreakpoint(355, 424, AQI_CATEGORY["very_unhealthy"]),
            AQIBreakpoint(425, 604, AQI_CATEGORY["hazardous"]),
        ],
    ),
}
