import math
from collections.abc import Sequence

from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.util.unit_conversion import (
    CarbonMonoxideConcentrationConverter,
    NitrogenDioxideConcentrationConverter,
    OzoneConcentrationConverter,
    SulphurDioxideConcentrationConverter,
)

from custom_components.air_quality_metrics.metrics.epa.types import AQISensorConfig


def truncate_concentration(concentration: float, precision: int) -> float:
    """Truncates a float value to a strict decimal place requirement."""
    if precision == 0:
        return float(math.floor(concentration))
    factor = 10**precision
    return math.floor(concentration * factor) / factor


def get_unit_normalizer(device_class: SensorDeviceClass, expected_unit: str):
    """Returns a lambda that normalizes incoming metrics to an expected unit."""

    if device_class == SensorDeviceClass.CO:
        converter = CarbonMonoxideConcentrationConverter
    elif device_class == SensorDeviceClass.NITROGEN_DIOXIDE:
        converter = NitrogenDioxideConcentrationConverter
    elif device_class == SensorDeviceClass.OZONE:
        converter = OzoneConcentrationConverter
    elif device_class == SensorDeviceClass.SULPHUR_DIOXIDE:
        converter = SulphurDioxideConcentrationConverter
    else:
        # Define a clean inner function instead of a restricted lambda
        def fallback_normalizer(value: float, from_unit: str) -> float:
            if from_unit == expected_unit:
                return value
            raise ValueError(
                f"No converter available for {device_class} to change "
                f"'{from_unit}' to '{expected_unit}'"
            )

        return fallback_normalizer

    # Standard converter closure
    return lambda value, from_unit: (
        value
        if from_unit == expected_unit
        else converter.convert(value, from_unit, expected_unit)
    )


def extract_valid_values(data: Sequence[int | float | None]) -> list[int | float]:
    """Remove all values from data that are not numbers greater than or equal to zero"""
    return [x for x in data if x is not None and x >= 0]


def estimate_hours_until_valid(
    window_size: int,
    require_valid: int,
    hourly_data: Sequence | None = None,
) -> int:
    """
    Given a list of hourly_data, estimate number of hours until there is enough data.

    This is used to estimate when certain calculations will have gathered enough
    data to be considered valid (readings that exist and are larger than zero).

    E.g.

    - AQI requires data for 75% (18 hours) out of the last 24 hours.
    - NowCast requires 2 out of the last 3 hours.

    Note: Don't call this directly. In order to avoid typos, there are helper functions
    for each type of metric.
    """
    if require_valid > window_size:
        raise ValueError(
            f"Required valid hours ({require_valid}) cannot exceed the total window size ({window_size})."
        )

    if hourly_data:
        # Pad the window to the configured window_size so range() works below
        simulation_window = list(hourly_data[:window_size]) + [None] * max(
            0, window_size - len(hourly_data)
        )

        # Early exit: If the data inside the active window already meets the criteria, 0 hours remain.
        if len(extract_valid_values(simulation_window)) >= require_valid:
            return 0

        # The maximum distance a data point can travel before exiting the window is window_size + 1
        for hours_forward in range(1, window_size + 1):
            # Pop off the final "hour"
            simulation_window.pop()
            # Add a new dummy valid data point for the "new" hour
            simulation_window.insert(0, 1)
            # Do we have enough data now?
            if len(extract_valid_values(simulation_window)) >= require_valid:
                return hours_forward

    return require_valid


def calculate_aqi(
    concentration: float,
    config: AQISensorConfig | None,
) -> int | None:
    """
    Calculate EPA AQI for the given config and concentration.

    The EPA formula is used by a number of metrics including AQI, NowCast, and IAQI.
    """
    if not config:
        return None

    # Protect against negative sensor readings
    concentration = max(0.0, concentration)

    # Truncate according to the sensor configuration
    concentration = truncate_concentration(concentration, config.precision)
    breakpoints = config.breakpoints

    # Handle scenario where reading is below the lowest defined threshold
    if concentration < breakpoints[0].low:
        return None

    # FIXME: we should only do this if the highest breakpoint is the highest category (see "ozone.8hour")
    # Handle 'Beyond the AQI' levels (extrapolate beyond the highest category)
    if concentration > breakpoints[-1].high:
        bp = breakpoints[-1]
        if bp.high == bp.low:
            return bp.idx_high

        aqi = ((bp.idx_high - bp.idx_low) / (bp.high - bp.low)) * (
            concentration - bp.low
        ) + bp.idx_low
        return round(aqi)

    # General Case: Normal interpolation within a standard bucket
    for bp in breakpoints:
        if bp.low <= concentration <= bp.high:
            if bp.high == bp.low:
                return bp.idx_low

            aqi = ((bp.idx_high - bp.idx_low) / (bp.high - bp.low)) * (
                concentration - bp.low
            ) + bp.idx_low
            return round(aqi)

    return None
