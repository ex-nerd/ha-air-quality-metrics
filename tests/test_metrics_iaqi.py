"""Tests for the Indoor IAQI calculation logic."""

from homeassistant.components.sensor import SensorDeviceClass

from custom_components.air_quality_metrics.metrics.atmotube.config import (
    IAQI_CATEGORY,
    IAQI_CONFIGS,
)
from custom_components.air_quality_metrics.metrics.helpers import calculate_aqi


class TestIndoorIAQICalculations:
    """Container for testing Indoor Air Quality Index (IAQI) mathematical mappings."""

    def test_iaqi_categories_are_ordered(self):
        """Ensure AQI_CATEGORIES is ordered strictly from lowest to highest threshold.

        This protects the loop optimization in get_aqi_attributes() from breaking
        if someone shuffles the dictionary keys in the future.
        """
        previous_low = 101

        # Note: IAQI indexes are inverted such that "low" is a larger number than "high"
        for key, category in IAQI_CATEGORY.items():
            # Assert that the current high index is greater than the previous one
            assert category.idx_low < previous_low, (
                f"AQI category ordering failure! The key '{key}' has an idx_idx_lowhigh of "
                f"{category.idx_low}, which is not lower than the preceding threshold ({previous_low}). "
                f"Ensure the dictionary is sorted from lowest threshold to highest."
            )

            # Also validate internal consistency of IAQICategory instances
            assert category.idx_low > category.idx_high, (
                f"AQICategory '{key}' has a lower bound ({category.idx_low}) "
                f"smaller than its upper bound ({category.idx_high})."
            )

            previous_low = category.idx_high

    def test_calculate_iaqi_pm1(self):
        """Ensure calculate_aqi accurately processes pm1 IAQI."""

        config = IAQI_CONFIGS.get(SensorDeviceClass.PM1)

        result = calculate_aqi(0, config)
        assert result == 100

    def test_calculate_iaqi_pm25(self):
        """Ensure calculate_aqi accurately processes pm2.5 IAQI."""

        config = IAQI_CONFIGS.get(SensorDeviceClass.PM25)

        result = calculate_aqi(12.0, config)
        assert result == 89
