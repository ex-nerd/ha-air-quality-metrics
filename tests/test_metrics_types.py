import pytest
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.const import (
    CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
)

from custom_components.air_quality_metrics.metrics.epa.types import (
    AQIBreakpoint,
    AQICategory,
    AQICategoryGrouping,
    AQISensorConfig,
)


class TestAQISensorConfigPipeline:
    """Complete test suite for validation, mapping, and conversion models."""

    @pytest.fixture
    def mock_categories(self) -> AQICategoryGrouping:
        """Provide basic AQICategory instances for relation mapping tests."""
        return {
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
        }

    def test_ozone_is_still_ozone(self):
        """Ensures that Home Assistant hasn't changed the ozone constant and broken AQISensorType"""
        assert SensorDeviceClass.OZONE == "ozone"

    def test_aqi_category_invalid_bounds(self):
        """Validate that inversion or equality of low/high indices triggers a ValueError."""
        with pytest.raises(ValueError, match="must be less than idx_high"):
            AQICategory(
                category="good",
                color_name="green",
                color="#00e400",
                color_assist="#9eff91",
                idx_low=50,
                idx_high=50,  # Invalid: low cannot equal high
            )

    def test_aqi_breakpoint_property_passthrough(self, mock_categories):
        """Ensure AQIBreakpoint correctly passes down dynamic index bounds from its Category."""
        breakpoint_mapping = AQIBreakpoint(
            low=0.0, high=12.0, category=mock_categories["good"]
        )

        # Ensure properties mirror the category definitions
        assert breakpoint_mapping.idx_low == 0
        assert breakpoint_mapping.idx_high == 50

    def test_breakpoint_sorting_on_config_init(self, mock_categories):
        """Ensure configuration instances always enforce monotonic ordering on inner elements."""
        bp_mid = AQIBreakpoint(
            low=12.1, high=35.4, category=mock_categories["moderate"]
        )
        bp_low = AQIBreakpoint(low=0.0, high=12.0, category=mock_categories["good"])

        # Be explicit with the typing because ty doesn't seem to understand the generics with defaults
        config = AQISensorConfig(
            unit=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
            precision=1,
            # Unsorted input
            breakpoints=[
                bp_mid,
                bp_low,
            ],
        )

        # Confirm the object.__setattr__ post_init hook mutated it cleanly
        assert config.breakpoints == [bp_low, bp_mid]
