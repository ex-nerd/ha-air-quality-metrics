"""Data coordinator for Indoor air quality metrics."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import cast  # Added for type compliance without hardcoded strings

from homeassistant.components.recorder import history
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from custom_components.air_quality_metrics.const import (
    CONF_SCAN_INTERVAL,
    CONF_SENSORS,
    INDOOR_DEVICE_TYPES,
)
from custom_components.air_quality_metrics.metrics.atmotube.config import IAQI_CONFIGS
from custom_components.air_quality_metrics.metrics.atmotube.types import IAQISensorType
from custom_components.air_quality_metrics.metrics.helpers import (
    calculate_aqi,
    get_unit_normalizer,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class PollutantMetrics:
    """Container for processed individual pollutant metrics."""

    iaqi: int | None


@dataclass(frozen=True)
class AirQualityCalculations:
    """Container for the unified final coordinator calculation results."""

    iaqi: int | None
    iaqi_primary: str | None


class IndoorDataCoordinator(DataUpdateCoordinator[AirQualityCalculations]):
    """Manages central history fetching and processes multi-pollutant Indoor air quality metrics."""

    def __init__(self, hass: HomeAssistant, entry):
        """Initialize the data coordinator."""
        self.scan_interval_minutes = entry.options.get(
            CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, 5)
        )

        super().__init__(
            hass,
            _LOGGER,
            name=f"Indoor Air Quality Coordinator ({entry.title})",
            update_interval=timedelta(minutes=self.scan_interval_minutes),
        )
        self.entry = entry
        self.sensors = entry.data.get(CONF_SENSORS, [])
        self.last_update_success_time: datetime | None = None

        _LOGGER.debug(
            "[%s] Indoor Coordinator initialized. Listening for %s entities.",
            self.entry.title,
            len(self.sensors),
        )

        # Hook into Home Assistant's core boot confirmation architecture
        if hass.state is not CoreState.running:

            async def _force_startup_refresh(_):
                _LOGGER.debug(
                    "[%s] Home Assistant core is fully up. Triggering immediate sensor evaluation.",
                    entry.title,
                )
                await self.async_refresh()

            hass.bus.async_listen_once(
                EVENT_HOMEASSISTANT_STARTED, _force_startup_refresh
            )

    def _get_current_mapped_sensors(self) -> dict[IAQISensorType, list[str]]:
        """Dynamically discover available sensors based on current state engine device_classes."""
        # Type the dictionary keys using your explicit literal type
        mapped: dict[IAQISensorType, list[str]] = {
            cast(IAQISensorType, key): [] for key in INDOOR_DEVICE_TYPES
        }

        for sensor_id in self.sensors:
            state_obj = self.hass.states.get(sensor_id)
            if not state_obj:
                _LOGGER.debug(
                    "[%s] Sensor %s is currently unavailable; skipping this cycle.",
                    self.entry.title,
                    sensor_id,
                )
                continue

            device_class = state_obj.attributes.get("device_class")

            # Since INDOOR_DEVICE_TYPES holds enum properties, checking containment here
            # validates that the runtime string is mathematically identical to a valid type.
            if device_class in INDOOR_DEVICE_TYPES:
                # Cast the string device_class directly to the IAQISensorType literal boundary
                mapped[cast(IAQISensorType, device_class)].append(sensor_id)

        return mapped

    async def _async_update_data(self) -> AirQualityCalculations:
        """Fetch short historical data once and compute compound indoor pollutant metrics."""
        mapped_sensors = self._get_current_mapped_sensors()
        active_entities = [
            ent for ent_list in mapped_sensors.values() for ent in ent_list
        ]

        if not active_entities:
            self.update_interval = timedelta(seconds=30)
            _LOGGER.debug(
                "[%s] Target entities aren't loaded yet. Setting rapid retry window (30s).",
                self.entry.title,
            )
            return AirQualityCalculations(iaqi=None, iaqi_primary=None)

        # Restore normal polling interval
        normalized_interval = timedelta(minutes=self.scan_interval_minutes)
        if self.update_interval != normalized_interval:
            self.update_interval = normalized_interval
            _LOGGER.info(
                "[%s] Sensors discovered. Returning to standard update profile.",
                self.entry.title,
            )

        end_time = dt_util.utcnow()

        # See documentation in _process_pollutant_metrics. IAQI wants the most
        # recent minute worth of data, but the scan interval might be wider than
        # that and we might not even have new data during that time period. Do
        # our best to ensure we capture the state that was active right as the
        # interval started.
        lookback_minutes = self.scan_interval_minutes + 1
        start_time = end_time - timedelta(minutes=lookback_minutes)

        try:
            history_dict = await self.hass.async_add_executor_job(
                history.get_significant_states,
                self.hass,
                start_time,
                end_time,
                active_entities,
            )
        except Exception as err:
            raise UpdateFailed(
                f"Database error fetching historical states: {err}"
            ) from err

        computed_metrics: dict[IAQISensorType, PollutantMetrics] = {}
        for p_type, entity_ids in mapped_sensors.items():
            if entity_ids:
                computed_metrics[p_type] = self._process_pollutant_metrics(
                    entity_ids, history_dict, p_type, end_time
                )

        # Extract the minimum IAQI value and resolve primary pollutant
        min_iaqi: int | None = None
        primary_pollutant: str | None = None

        for p_type, metric in computed_metrics.items():
            if metric.iaqi is not None:
                if min_iaqi is None or metric.iaqi < min_iaqi:
                    min_iaqi = metric.iaqi
                    primary_pollutant = str(p_type)

        self.last_update_success_time = end_time

        return AirQualityCalculations(iaqi=min_iaqi, iaqi_primary=primary_pollutant)

    def _process_pollutant_metrics(
        self,
        sensor_ids: list[str],
        history_dict: dict,
        sensor_type: IAQISensorType,
        end_time: datetime,
    ) -> PollutantMetrics:
        """
        Calculate the metrics for a specific sensor type.

        Because IAQI is calculated from the readings averaged over the most
        recent minute, and Home Assistant might not have readings if the value
        has remained unchanged or fails to report in, we jump through a few
        hoops to produce the best value that we can.
        """
        sensor_config = IAQI_CONFIGS[sensor_type]
        normalize_unit = get_unit_normalizer(sensor_type, sensor_config.unit)

        # We try to get data for the last 60 seconds first
        samples: list[float] = []

        for entity_id in sensor_ids:
            state_obj = self.hass.states.get(entity_id)
            unit = (
                state_obj.attributes.get("unit_of_measurement", "") if state_obj else ""
            )

            # Walk history items for this sensor
            for state in history_dict.get(entity_id, []):
                time_delta = (end_time - state.last_updated).total_seconds()

                try:
                    val = float(state.state)
                    if val < 0:
                        continue

                    normalized_val = normalize_unit(val, unit)

                    # Group 1: Strict 1-minute window
                    if 0 <= time_delta <= 60:
                        samples.append(normalized_val)

                except ValueError, TypeError, HomeAssistantError:
                    continue

        if samples:
            # If we can, use the most recent minute worth of data
            _LOGGER.debug(
                "[%s] (%s) Using strict 1-minute average window.",
                self.entry.title,
                sensor_type,
            )

        elif state_obj:
            # Otherwise, fall back to the current state engine snapshot
            # TODO: should we set a maximum age for old data?
            _LOGGER.debug(
                "[%s] (%s) History dry for full interval. Falling back to current state.",
                self.entry.title,
                sensor_type,
            )
            try:
                val = float(state_obj.state)
                samples = [normalize_unit(val, unit)] if val >= 0 else []
            except ValueError, TypeError:
                samples = []
        else:
            samples = []

        # Calculate average and translate to IAQI
        if samples:
            avg_concentration = sum(samples) / len(samples)
            iaqi = calculate_aqi(avg_concentration, sensor_config)
        else:
            iaqi = None

        return PollutantMetrics(iaqi=iaqi)
