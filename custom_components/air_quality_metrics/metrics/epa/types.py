# Define the allowed sensor types.
from dataclasses import dataclass
from typing import Literal

from homeassistant.components.sensor import SensorDeviceClass

from custom_components.air_quality_metrics.metrics.types import (
    AQIBreakpointBase,
    AQICategoryBase,
    AQISensorConfigBase,
)

# Strings that correspond to home assistant device_class values,
# with optional dot-separated variant
AQISensorType = Literal[
    SensorDeviceClass.CO,
    SensorDeviceClass.NITROGEN_DIOXIDE,
    SensorDeviceClass.PM10,
    SensorDeviceClass.PM25,
    SensorDeviceClass.SULPHUR_DIOXIDE,
    # Typecheck won't allow us to build a string with SensorDeviceClass.OZONE
    "ozone.1hour",
    "ozone.8hour",
]


AQICategoryName = Literal[
    "good",
    "moderate",
    "unhealthy_sensitive",
    "unhealthy",
    "very_unhealthy",
    "hazardous",
]

AQIColorName = Literal[
    "green",
    "yellow",
    "orange",
    "red",
    "purple",
    "maroon",
]


@dataclass(frozen=True)
class AQICategory(AQICategoryBase):
    """
    Data class for EPA AQI category and color mapping.

    Attributes:
        category: normalized category name for dictionary indices, translation keys, etc.
        color_name: Color name (e.g. green)
        color: Hex code for standard color
        color_assist: Hex code for ColorVision Assist color variant
        idx_low: The lower bound AQI index score for this category.
        idx_high: The upper bound AQI index score for this category.
    """

    category: AQICategoryName
    color_name: AQIColorName
    color: str
    color_assist: str

    idx_low: int
    idx_high: int

    def __post_init__(self) -> None:
        if self.idx_low >= self.idx_high:
            raise ValueError(
                f"Invalid AQI boundaries for '{self.category}': "
                f"idx_low ({self.idx_low}) must be less than idx_high ({self.idx_high})."
            )


AQICategoryGrouping = dict[AQICategoryName, AQICategory]


@dataclass(frozen=True)
class AQIBreakpoint[CategoryT: AQICategory = AQICategory](AQIBreakpointBase[CategoryT]):
    low: float
    high: float
    category: CategoryT


@dataclass(frozen=True)
class AQISensorConfig(AQISensorConfigBase[AQIBreakpoint[AQICategory]]):
    unit: str
    precision: int
    breakpoints: list[AQIBreakpoint[AQICategory]]

    def __post_init__(self):
        self._sort_breakpoints()
