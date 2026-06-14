"""Tests for the Indoor Air Quality Data Coordinator and Sensors."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from unittest.mock import ANY, MagicMock, patch

import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import CONCENTRATION_MICROGRAMS_PER_CUBIC_METER
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import dt as dt_util

from custom_components.air_quality_metrics.const import CONF_SENSORS
from custom_components.air_quality_metrics.metrics.epa.types import AQICategory
from custom_components.air_quality_metrics.sensors.indoor.coordinator import (
    AirQualityCalculations,
    IndoorDataCoordinator,
)
from custom_components.air_quality_metrics.sensors.indoor.iaqi import (
    IAQICategorySensor,
    IAQIColorSensor,
    IAQIPrimaryPollutantSensor,
    IAQISensor,
)


@dataclass
class MockState:
    """Mock Home Assistant entity state object for recorder history."""

    state: str
    last_updated: datetime
    attributes: dict | None = None


@pytest.fixture
def mock_hass():
    """Fixture to provide a mocked HomeAssistant instance with State Engine support."""
    hass = MagicMock()
    mock_state_obj = MagicMock()
    mock_state_obj.attributes = {
        "unit_of_measurement": CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
        "device_class": SensorDeviceClass.PM25,
    }
    hass.states.get.return_value = mock_state_obj
    return hass


@pytest.fixture
def mock_config_entry():
    """Fixture to provide a mocked Home Assistant ConfigEntry using the indoor sensor config."""
    entry = MagicMock()
    entry.entry_id = "mock_entry_id_123"
    entry.title = "Indoor Test Location"
    entry.data = {
        CONF_SENSORS: ["sensor.living_room_pm25", "sensor.living_room_co2"],
        "scan_interval": 5,
    }
    entry.options = {}
    return entry


@pytest.fixture
def coordinator(mock_hass, mock_config_entry):
    """Fixture to provide an initialized indoor data coordinator instance."""
    with patch(
        "custom_components.air_quality_metrics.sensors.indoor.coordinator.DataUpdateCoordinator.__init__"
    ):
        coord = IndoorDataCoordinator(mock_hass, mock_config_entry)
        coord.hass = mock_hass
        coord.entry = mock_config_entry
        # Fix: Seed the underlying protected property since parent __init__ was patched out
        coord._update_interval = timedelta(minutes=5)
        return coord


# =========================================================================
# Coordinator Unit Tests
# =========================================================================


class TestIndoorCoordinator:
    """Container for testing calculation profiles in the Indoor Air Quality Data Coordinator."""

    @patch(
        "custom_components.air_quality_metrics.sensors.indoor.coordinator.calculate_aqi"
    )
    @patch(
        "custom_components.air_quality_metrics.sensors.indoor.coordinator.get_unit_normalizer"
    )
    def test_process_pollutant_metrics_prefer_1min_window(
        self, mock_get_normalizer, mock_calc_aqi, coordinator
    ):
        """History contains recent data. Ensure it uses the strict 1-minute window over interval fallback."""
        mock_normalizer = MagicMock(side_effect=lambda val, unit: val)
        mock_get_normalizer.return_value = mock_normalizer
        mock_calc_aqi.return_value = 42

        now = dt_util.utcnow()
        # State updated 30 seconds ago (falls within 1-minute strict window)
        state_recent = MockState(state="12.0", last_updated=now - timedelta(seconds=30))
        # State updated 3 minutes ago (falls only within scan interval window)
        state_older = MockState(state="45.0", last_updated=now - timedelta(minutes=3))

        history_dict = {"sensor.living_room_pm25": [state_recent, state_older]}

        # Mock the current state snapshot configuration using HA core unit constants
        mock_state_obj = MagicMock()
        mock_state_obj.attributes = {
            "unit_of_measurement": CONCENTRATION_MICROGRAMS_PER_CUBIC_METER
        }
        coordinator.hass.states.get.return_value = mock_state_obj

        metrics = coordinator._process_pollutant_metrics(
            ["sensor.living_room_pm25"], history_dict, SensorDeviceClass.PM25, now
        )

        assert metrics.iaqi == 42
        # Verify average calculated solely using the 1-minute sample (sum: 12.0 / len: 1 = 12.0)
        mock_calc_aqi.assert_called_once_with(12.0, ANY)

    @patch(
        "custom_components.air_quality_metrics.sensors.indoor.coordinator.calculate_aqi"
    )
    @patch(
        "custom_components.air_quality_metrics.sensors.indoor.coordinator.get_unit_normalizer"
    )
    def test_process_pollutant_metrics_fallback_to_current_state(
        self, mock_get_normalizer, mock_calc_aqi, coordinator
    ):
        """History is completely dry. Ensure it grabs a sample from the current state engine fallback."""
        mock_normalizer = MagicMock(side_effect=lambda val, unit: val)
        mock_get_normalizer.return_value = mock_normalizer
        mock_calc_aqi.return_value = 15

        now = dt_util.utcnow()
        history_dict = {"sensor.living_room_pm25": []}

        # Mock state engine snapshot to return a current state value of 10.0 and correct HA core unit constant
        mock_state_obj = MagicMock()
        mock_state_obj.state = "10.0"
        mock_state_obj.attributes = {
            "unit_of_measurement": CONCENTRATION_MICROGRAMS_PER_CUBIC_METER
        }
        coordinator.hass.states.get.return_value = mock_state_obj

        metrics = coordinator._process_pollutant_metrics(
            ["sensor.living_room_pm25"], history_dict, SensorDeviceClass.PM25, now
        )

        assert metrics.iaqi == 15
        mock_calc_aqi.assert_called_once_with(10.0, ANY)

    @patch(
        "custom_components.air_quality_metrics.sensors.indoor.coordinator.history.get_significant_states"
    )
    async def test_async_update_data_database_failure(
        self, mock_get_states, coordinator
    ):
        """Database connection error or engine query fault. Verifies UpdateFailed exception routing."""
        mock_get_states.side_effect = Exception("Connection lost")

        # Partially prepare a target mapping so discovery passes execution over to database fetcher
        mock_state_obj = MagicMock()
        mock_state_obj.attributes = {"device_class": SensorDeviceClass.PM25}
        coordinator.hass.states.get.return_value = mock_state_obj

        # Emulate the executor block framework inside Home Assistant
        coordinator.hass.async_add_executor_job = lambda func, *args, **kwargs: func(
            *args, **kwargs
        )

        with pytest.raises(UpdateFailed) as exc_info:
            await coordinator._async_update_data()

        assert "Database error fetching historical states" in str(exc_info.value)


# =========================================================================
# Sensor Entity Unit Tests
# =========================================================================


class TestIndoorSensors:
    """Container for testing localized state evaluations across the indoor tracking entities."""

    @pytest.fixture
    def mock_epa_category(self):
        """Helper fixture generating a structured mock translation dataclass container."""
        return AQICategory(
            category="unhealthy_sensitive",
            color_name="orange",
            color="#FF7E00",
            color_assist="#FF9E3B",
            idx_low=101,
            idx_high=150,
        )

    def test_iaqi_sensor_properties(self, coordinator, mock_config_entry):
        """Verifies primary composite measurement properties and explicit unique naming bindings."""
        coordinator.data = AirQualityCalculations(iaqi=75, iaqi_primary="pm25")
        sensor = IAQISensor(coordinator, mock_config_entry)

        assert sensor.native_value == 75
        assert sensor.state_class == SensorStateClass.MEASUREMENT
        assert sensor.device_class == SensorDeviceClass.AQI
        assert sensor.unique_id == "mock_entry_id_123_iaqi"

    def test_iaqi_primary_pollutant_sensor_icon_mapping(
        self, coordinator, mock_config_entry
    ):
        """Verifies icon shifts dynamically depending on underlying device class parameters."""
        coordinator.data = AirQualityCalculations(iaqi=85, iaqi_primary="pm25")
        sensor = IAQIPrimaryPollutantSensor(coordinator, mock_config_entry)

        # PM25 or PM10 primary targets must shift icon profiles to blur variants
        assert sensor.native_value == "pm25"
        assert sensor.icon == "mdi:blur"

        # CO, OZONE, or unexpected entities switch over to chemical molecule variants
        coordinator.data = AirQualityCalculations(
            iaqi=40, iaqi_primary="carbon_monoxide"
        )
        assert sensor.native_value == "carbon_monoxide"
        assert sensor.icon == "mdi:molecule"

    @patch(
        "custom_components.air_quality_metrics.sensors.indoor.iaqi.get_aqi_attributes"
    )
    def test_iaqi_category_sensor_evaluation(
        self, mock_get_attrs, coordinator, mock_config_entry, mock_epa_category
    ):
        """Verifies category state parsing and dynamic theme lookup structures."""
        mock_get_attrs.return_value = mock_epa_category
        coordinator.data = AirQualityCalculations(iaqi=120, iaqi_primary="pm25")

        sensor = IAQICategorySensor(coordinator, mock_config_entry)
        assert sensor.native_value == "unhealthy_sensitive"

    @patch(
        "custom_components.air_quality_metrics.sensors.indoor.iaqi.get_aqi_attributes"
    )
    def test_iaqi_color_sensor_evaluation(
        self, mock_get_attrs, coordinator, mock_config_entry, mock_epa_category
    ):
        """Verifies hex profile routing extracts values matching core metric calculations."""
        mock_get_attrs.return_value = mock_epa_category
        coordinator.data = AirQualityCalculations(iaqi=120, iaqi_primary="pm25")

        sensor = IAQIColorSensor(coordinator, mock_config_entry)
        assert sensor.native_value == "#FF7E00"

    def test_base_sensor_fallback_icon(self, coordinator, mock_config_entry):
        """Verifies system defaults to a clock placeholder icon if values are unavailable."""
        coordinator.data = AirQualityCalculations(iaqi=None, iaqi_primary=None)
        sensor = IAQISensor(coordinator, mock_config_entry)

        assert sensor.native_value is None
        assert sensor.icon == "mdi:database-clock-outline"
