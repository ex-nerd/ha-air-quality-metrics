from abc import ABC


class AQICategoryBase(ABC):
    """Base class that can be used for any data usable in the AQI formula."""

    category: str
    idx_low: int
    idx_high: int


class AQIBreakpointBase[CategoryT: AQICategoryBase](ABC):
    """Represents a single concentration-to-index interval mapping.

    This generic base class represents the breakpoints used in the AQI
    calculation, which is used by both outdoor EPA and some indoor metrics.

    Attributes:
        low: The lower bound concentration threshold for this breakpoint.
        high: The upper bound concentration threshold for this breakpoint.
        category: AQICategory associated with this breakpoint
        idx_low: From category, the lower bound AQI index score for this breakpoint.
        idx_high: From category, the upper bound AQI index score for this breakpoint.
    """

    low: float
    high: float
    category: CategoryT

    @property
    def idx_low(self) -> int:
        return self.category.idx_low

    @property
    def idx_high(self) -> int:
        return self.category.idx_high


class AQISensorConfigBase[BreakpointT: AQIBreakpointBase](ABC):
    """
    Encapsulates the truncation precision and AQI breakpoints for a sensor type.

    Attributes:
        units: The expected units for calculation (so we can convert or reject, as necessary).
        precision: The number of decimal places to truncate raw data to.
        breakpoints: The ordered list of breakpoint mappings for the sensor type.
    """

    unit: str
    precision: int
    breakpoints: list[BreakpointT]

    def _sort_breakpoints(self) -> None:
        """
        Enforces that breakpoints are always sorted by concentration low-bound.

        Must be called via the subclass's own __post_init__ method.
        """
        # Sort by low ascending
        sorted_bps = sorted(self.breakpoints, key=lambda bp: bp.low)

        # Safely assign to the frozen instance
        object.__setattr__(self, "breakpoints", sorted_bps)
