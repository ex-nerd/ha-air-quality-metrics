import math
from decimal import Decimal

from custom_components.air_quality_metrics.metrics.epa.config import (
    AQI_CATEGORY,
    AQI_CONFIGS,
)


def has_invalid_precision(value: float, allowed_precision: int) -> bool:
    """Returns True if a float value has more decimal places than allowed."""
    decimal_val = Decimal(str(value))
    exponent = decimal_val.as_tuple().exponent

    # Type Guard: If the exponent is a string flag ("n", "N", "F"),
    # it's an invalid floating point representation for a normal config value.
    if isinstance(exponent, str):
        return True

    # The type checker now safely knows 'exponent' can ONLY be an int here!
    actual_precision = abs(exponent)

    return actual_precision > allowed_precision


class TestMetricsEPATypes:
    def test_aqi_categories_are_ordered(self):
        """Ensure AQI_CATEGORIES is ordered strictly from lowest to highest threshold.

        This protects the loop optimization in get_aqi_attributes() from breaking
        if someone shuffles the dictionary keys in the future.
        """
        previous_high = -1

        for key, category in AQI_CATEGORY.items():
            # Assert that the current high index is greater than the previous one
            assert category.idx_high > previous_high, (
                f"AQI category ordering failure! The key '{key}' has an idx_high of "
                f"{category.idx_high}, which is not greater than the preceding threshold ({previous_high}). "
                f"Ensure the dictionary is sorted from lowest threshold to highest."
            )

            # Also validate internal consistency of AQICategory instances
            assert category.idx_low <= category.idx_high, (
                f"AQICategory '{key}' has a lower bound ({category.idx_low}) "
                f"greater than its upper bound ({category.idx_high})."
            )

            previous_high = category.idx_low

    def test_aqi_configs(self):
        """Verify that AQI_CONFIGS are logically consistent.

        Verifies that no mathematical/index gaps exist within any sensor configurations
        and that all defined concentration values strictly match the sensor's precision.
        """
        for sensor_type, config in AQI_CONFIGS.items():
            breakpoints = config.breakpoints
            precision = config.precision

            # Determine step size based on precision rules (e.g., precision 1 -> 0.1 step)
            concentration_step = 10 ** (-precision) if precision > 0 else 1.0

            for i, current_bp in enumerate(breakpoints):
                # 1. Validate concentration value precision bounds
                assert not has_invalid_precision(current_bp.low, precision), (
                    f"Precision mismatch in '{sensor_type}'! "
                    f"low={current_bp.low} exceeds the allowed precision of {precision} decimal places."
                )
                assert not has_invalid_precision(current_bp.high, precision), (
                    f"Precision mismatch in '{sensor_type}'! "
                    f"high={current_bp.high} exceeds the allowed precision of {precision} decimal places."
                )

                # Continuity checks against the next breakpoint
                if i < len(breakpoints) - 1:
                    next_bp = breakpoints[i + 1]

                    # 2. Assert Concentration Continuity
                    expected_c_low = current_bp.high + concentration_step
                    assert math.isclose(next_bp.low, expected_c_low, rel_tol=1e-9), (
                        f"Concentration gap in '{sensor_type}'! "
                        f"Expected next low to be {expected_c_low}, found {next_bp.low}"
                    )

                    # 3. Assert AQI Index Continuity
                    expected_i_low = current_bp.idx_high + 1
                    assert next_bp.idx_low == expected_i_low, (
                        f"AQI Index gap in '{sensor_type}'! "
                        f"Expected next idx_low to be {expected_i_low}, found {next_bp.idx_low}"
                    )
