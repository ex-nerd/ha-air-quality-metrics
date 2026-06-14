from custom_components.air_quality_metrics.metrics.epa.config import (
    AQI_CATEGORY,
)
from custom_components.air_quality_metrics.metrics.epa.types import (
    AQICategory,
)
from custom_components.air_quality_metrics.metrics.helpers import (
    estimate_hours_until_valid,
)


def get_aqi_attributes(aqi: float | int) -> AQICategory:
    """Return the EPA category and color information for a given AQI."""
    for category in AQI_CATEGORY.values():
        if aqi <= category.idx_high:
            return category
    return AQI_CATEGORY["hazardous"]


def estimate_hours_until_daily_valid(hourly_averages: list | None = None) -> int:
    """Wrapper around estimate_hours_until_valid for daily AQI window size"""
    return estimate_hours_until_valid(
        window_size=24, require_valid=18, hourly_data=hourly_averages
    )


def estimate_hours_until_nowcast_valid(hourly_averages: list | None = None) -> int:
    """Wrapper around estimate_hours_until_valid for NowCast window size"""
    return estimate_hours_until_valid(
        window_size=3, require_valid=2, hourly_data=hourly_averages
    )
