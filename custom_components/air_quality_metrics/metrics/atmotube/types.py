from dataclasses import dataclass
from typing import Literal

from homeassistant.components.sensor import SensorDeviceClass

from custom_components.air_quality_metrics.metrics.types import (
    AQIBreakpointBase,
    AQICategoryBase,
    AQISensorConfigBase,
)

IAQISensorType = Literal[
    SensorDeviceClass.CO,
    SensorDeviceClass.CO2,
    SensorDeviceClass.PM1,
    SensorDeviceClass.PM10,
    SensorDeviceClass.PM25,
    SensorDeviceClass.OZONE,
]

IAQICategoryName = Literal[
    "good",
    "moderate",
    "polluted",
    "very_polluted",
    "severely_polluted",
]


@dataclass(frozen=True)
class IAQICategory(AQICategoryBase):
    """
    Data class for Atmotube IAQI category and color code.

    NOTE: IAQI index values are inverted so "low" is actually a larger number

    Attributes:
        category: normalized category name for dictionary indices, translation keys, etc.
        color: Hex code for standard color
        color_assist: Hex code for ColorVision Assist color variant
        idx_low: The lower bound AQI index score for this category.
        idx_high: The upper bound AQI index score for this category.
    """

    category: IAQICategoryName
    color: str

    idx_low: int
    idx_high: int

    def __post_init__(self) -> None:
        if self.idx_high >= self.idx_low:
            raise ValueError(
                f"Invalid IAQI boundaries for '{self.category}': "
                f"idx_high ({self.idx_high}) must be less than idx_low ({self.idx_low})."
            )


IAQICategoryGrouping = dict[IAQICategoryName, IAQICategory]


@dataclass(frozen=True)
class IAQIBreakpoint[CategoryT: IAQICategory = IAQICategory](
    AQIBreakpointBase[CategoryT]
):
    low: float
    high: float
    category: IAQICategory


@dataclass(frozen=True)
class IAQISensorConfig(AQISensorConfigBase[IAQIBreakpoint[IAQICategory]]):
    unit: str
    precision: int
    breakpoints: list[IAQIBreakpoint]

    def __post_init__(self):
        self._sort_breakpoints()
