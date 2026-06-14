import pytest

from custom_components.air_quality_metrics.metrics.helpers import (
    estimate_hours_until_valid,
)


class TestEstimateHoursUntilValid:
    def test_invalid_arguments(self):
        """Ensure a ValueError is raised if require_valid exceeds window_size."""
        with pytest.raises(ValueError, match="cannot exceed the total window size"):
            estimate_hours_until_valid(window_size=24, require_valid=25)

    @pytest.mark.parametrize(
        "hourly_data, expected",
        [
            (None, 18),
            ([], 18),
        ],
    )
    def test_empty_or_none_data(self, hourly_data: list | None, expected: int):
        """Ensure fallback value is returned immediately when no data exists."""
        assert estimate_hours_until_valid(24, 18, hourly_data) == expected

    def test_early_exit_already_valid(self):
        """Ensure 0 is returned immediately if the data already meets criteria."""
        # 18 valid data points out of 24
        valid_data = [1] * 18 + [None] * 6
        assert estimate_hours_until_valid(24, 18, valid_data) == 0

    def test_aqi_simulation_sliding_window(self):
        """Test standard 24-hour AQI windows needing future time blocks."""
        # Has 16 valid entries. Needs 2 more hours of data to hit 18.
        data_needing_2_hours = [1] * 16 + [None] * 8
        assert estimate_hours_until_valid(24, 18, data_needing_2_hours) == 2

        # Has 12 valid entries. Needs 6 more hours of data to hit 18.
        data_needing_6_hours = [1] * 12 + [None] * 12
        assert estimate_hours_until_valid(24, 18, data_needing_6_hours) == 6

    def test_short_list_padding_logic(self):
        """Verify data sets shorter than the window size calculate correctly via internal padding."""
        # Total array length is 5, with 4 valid entries.
        # For a 24-hour window, it structurally pads out the remaining 19 slots with None.
        # To get 18 valid data points, it needs 14 more hours (18 - 4).
        short_data = [1, 1, None, 1, 1]
        assert estimate_hours_until_valid(24, 18, short_data) == 14

    def test_nowcast_short_window(self):
        """Test NowCast calculations using a 2 out of 3 hour criteria."""
        # Data satisfies 2 out of 3 hours immediately
        already_valid_nowcast = [1, None, 1]
        assert estimate_hours_until_valid(3, 2, already_valid_nowcast) == 0

        # Data has only 1 valid point in the active 3-hour window.
        # Needs 1 hour of incoming data to get a second valid point.
        needing_1_hour_nowcast = [None, 1, None]
        assert estimate_hours_until_valid(3, 2, needing_1_hour_nowcast) == 1

        # Data has only 1 valid point in the active 3-hour window, but in the third hour.
        # Needs 2 hour of incoming data because the next hour will expire the third entry.
        needing_2_hours_nowcast = [None, None, 1]
        assert estimate_hours_until_valid(3, 2, needing_2_hours_nowcast) == 2

        # Data is full of None
        hourly_averages_all_empty = [None] * 24
        assert estimate_hours_until_valid(3, 2, hourly_averages_all_empty) == 2

        # Data has some entries valid entries but not in the initial window.
        hourly_averages_stale = [None] * 5 + [1, 1, 1, None]
        assert estimate_hours_until_valid(3, 2, hourly_averages_stale) == 2

    def test_estimate_hours_until_daily_valid(self):
        """Direct verification check on simulated look-ahead tracker for 24h Daily updates."""
        # Scenario A: Has 17 valid hours right now. Passing 1 single hour forward shifts a valid point in.
        hourly_averages_a = [1] * 17 + [None] * 7
        assert estimate_hours_until_valid(24, 18, hourly_averages_a) == 1

        # Scenario B: Completely empty list. Needs 18 simulated hours to roll in 18 valid measurements.
        hourly_averages_b = [None] * 24
        assert estimate_hours_until_valid(24, 18, hourly_averages_b) == 18
