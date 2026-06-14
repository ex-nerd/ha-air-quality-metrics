"""Data coordinator for outdoor air quality metrics."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from homeassistant.components.recorder import history
from homeassistant.components.sensor import SensorDeviceClass

# Home Assistant constants for your tracking
from homeassistant.const import (
    EVENT_HOMEASSISTANT_STARTED,
)
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from custom_components.air_quality_metrics.const import (
    CONF_SCAN_INTERVAL,
    CONF_SENSORS,
    OUTDOOR_DEVICE_TYPES,
)
from custom_components.air_quality_metrics.metrics.epa.config import AQI_CONFIGS
from custom_components.air_quality_metrics.metrics.epa.helpers import (
    estimate_hours_until_daily_valid,
)
from custom_components.air_quality_metrics.metrics.epa.nowcast import calculate_nowcast
from custom_components.air_quality_metrics.metrics.helpers import (
    calculate_aqi,
    get_unit_normalizer,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class OutdoorMetrics:
    """Container for processed individual pollutant metrics."""

    daily_aqi: int | None
    daily_hours_remaining: int
    nowcast_aqi: int | None
    nowcast_hours_remaining: int


@dataclass(frozen=True)
class OutdoorCalculations:
    """Container for the unified final coordinator calculation results."""

    daily_aqi: int | None
    daily_primary: str
    daily_available_at: datetime | None
    daily_activated_at: datetime | None
    nowcast_aqi: int | None
    nowcast_primary: str
    nowcast_available_at: datetime | None
    nowcast_activated_at: datetime | None


class OutdoorDataCoordinator(DataUpdateCoordinator[OutdoorCalculations]):
    """Manages central history fetching and processes multi-pollutant outdoor AQI."""

    def __init__(self, hass: HomeAssistant, entry):
        """Initialize the data coordinator."""

        self.scan_interval_minutes = entry.options.get(
            CONF_SCAN_INTERVAL, entry.data.get(CONF_SCAN_INTERVAL, 5)
        )

        super().__init__(
            hass,
            _LOGGER,
            name=f"Outdoor Air Quality Coordinator ({entry.title})",
            update_interval=timedelta(minutes=self.scan_interval_minutes),
        )
        self.entry = entry
        self.sensors = entry.data.get(CONF_SENSORS, [])
        self.last_update_success_time: datetime | None = None
        self._daily_activated_at: datetime | None = None
        self._nowcast_activated_at: datetime | None = None

        _LOGGER.debug(
            "[%s] Outdoor Coordinator initialized. Listening for %s entities.",
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

    def _get_current_mapped_sensors(self) -> dict[str, list[str]]:
        """Dynamically discover available sensors based on current state engine device_classes."""
        mapped: dict[str, list[str]] = {key: [] for key in OUTDOOR_DEVICE_TYPES}

        for sensor_id in self.sensors:
            state_obj = self.hass.states.get(sensor_id)
            if not state_obj:
                _LOGGER.debug(
                    "[%s] Sensor %s is currently unavailable in the state machine; skipping this cycle.",
                    self.entry.title,
                    sensor_id,
                )
                continue

            device_class = state_obj.attributes.get("device_class")
            if device_class in OUTDOOR_DEVICE_TYPES:
                mapped[device_class].append(sensor_id)

        return mapped

    def async_initialize_restored_timestamps(
        self,
        daily_activated_at: datetime | None = None,
        nowcast_activated_at: datetime | None = None,
    ) -> None:
        """Seed initial values restored from entity storage before the first database fetch."""
        if daily_activated_at is not None and self._daily_activated_at is None:
            self._daily_activated_at = daily_activated_at

        if nowcast_activated_at is not None and self._nowcast_activated_at is None:
            self._nowcast_activated_at = nowcast_activated_at

        if self.data is None:
            self.data = OutdoorCalculations(
                daily_aqi=None,
                daily_primary="None",
                daily_available_at=None,
                daily_activated_at=self._daily_activated_at,
                nowcast_aqi=None,
                nowcast_primary="None",
                nowcast_available_at=None,
                nowcast_activated_at=self._nowcast_activated_at,
            )

    async def _async_update_data(self) -> OutdoorCalculations:
        """Fetch historical data once and compute dynamic compound pollutant metrics."""
        mapped_sensors = self._get_current_mapped_sensors()
        active_entities = [
            ent for ent_list in mapped_sensors.values() for ent in ent_list
        ]

        if not active_entities:
            # If we are early in the boot track, compress the next update check to 30 seconds
            self.update_interval = timedelta(seconds=30)
            _LOGGER.debug(
                "[%s] Target entities aren't loaded yet. Setting rapid retry window (30s).",
                self.entry.title,
            )
            return OutdoorCalculations(
                daily_aqi=None,
                daily_primary="None",
                daily_available_at=None,
                daily_activated_at=self._daily_activated_at,
                nowcast_aqi=None,
                nowcast_primary="None",
                nowcast_available_at=None,
                nowcast_activated_at=self._nowcast_activated_at,
            )

        # Restore normal user-configured polling interval once target entities successfully latch on
        normalized_interval = timedelta(minutes=self.scan_interval_minutes)
        if self.update_interval != normalized_interval:
            self.update_interval = normalized_interval
            _LOGGER.info(
                "[%s] Sensors discovered and mapped successfully. Returning to standard update profile.",
                self.entry.title,
            )

        end_time = dt_util.utcnow()
        start_time = end_time - timedelta(hours=25)

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

        computed_metrics: dict[str, OutdoorMetrics] = {}

        # Process each configured pollutant group
        for p_type, entity_ids in mapped_sensors.items():
            if entity_ids:
                computed_metrics[p_type] = self._process_pollutant_metrics(
                    entity_ids, history_dict, p_type
                )

        # Evaluate highest matching daily AQI
        daily_aqi = None
        daily_primary = "None"
        daily_hours_left = []

        for p_type, metric in computed_metrics.items():
            if metric.daily_aqi is not None:
                if daily_aqi is None or metric.daily_aqi > daily_aqi:
                    daily_aqi = metric.daily_aqi
                    daily_primary = p_type
            else:
                daily_hours_left.append(metric.daily_hours_remaining)

        daily_available_at = (
            None
            if daily_aqi is not None or not daily_hours_left
            else end_time + timedelta(hours=min(daily_hours_left))
        )

        # Evaluate highest matching AQI
        nowcast_aqi = None
        nowcast_primary = "None"
        nowcast_hours_left = []

        for p_type, metric in computed_metrics.items():
            if metric.nowcast_aqi is not None:
                if nowcast_aqi is None or metric.nowcast_aqi > nowcast_aqi:
                    nowcast_aqi = metric.nowcast_aqi
                    nowcast_primary = p_type
            else:
                nowcast_hours_left.append(metric.nowcast_hours_remaining)

        nowcast_available_at = (
            None
            if nowcast_aqi is not None or not nowcast_hours_left
            else end_time + timedelta(hours=min(nowcast_hours_left))
        )

        if daily_aqi is not None and (
            self._daily_activated_at is None or self._daily_activated_at > end_time
        ):
            self._daily_activated_at = end_time
        if nowcast_aqi is not None and (
            self._nowcast_activated_at is None or self._nowcast_activated_at > end_time
        ):
            self._nowcast_activated_at = end_time

        self.last_update_success_time = end_time

        return OutdoorCalculations(
            daily_aqi=daily_aqi,
            daily_primary=daily_primary,
            daily_available_at=daily_available_at,
            daily_activated_at=self._daily_activated_at,
            nowcast_aqi=nowcast_aqi,
            nowcast_primary=nowcast_primary,
            nowcast_available_at=nowcast_available_at,
            nowcast_activated_at=self._nowcast_activated_at,
        )

    def _calculate_hourly_averages(
        self, sensor_ids, history_dict, sensor_type
    ) -> list[float | None]:
        buckets = [[] for _ in range(24)]
        end_time = dt_util.utcnow()

        # Note: Ozone 1- and 8-hour use the same unit so just pick one
        sensor_config = AQI_CONFIGS[
            "ozone.1hour" if sensor_type == SensorDeviceClass.OZONE else sensor_type
        ]
        normalize_unit = get_unit_normalizer(sensor_type, sensor_config.unit)

        for entity_id in sensor_ids:
            state_obj = self.hass.states.get(entity_id)
            unit = (
                state_obj.attributes.get("unit_of_measurement", "") if state_obj else ""
            )

            for state in history_dict.get(entity_id, []):
                time_delta = end_time - state.last_updated
                hours_ago = int(time_delta.total_seconds() // 3600)

                if 0 <= hours_ago < 24:
                    try:
                        val = float(state.state)
                        if val >= 0:
                            buckets[hours_ago].append(normalize_unit(val, unit))
                    except ValueError, TypeError, HomeAssistantError:
                        # Skip invalid data
                        continue

        return [(sum(bucket) / len(bucket)) if bucket else None for bucket in buckets]

    def _process_pollutant_metrics(
        self, sensor_ids, history_dict, sensor_type
    ) -> OutdoorMetrics:
        """Calculate the metrics for a specific sensor type, if enough readings are available to do so."""
        hourly_averages = self._calculate_hourly_averages(
            sensor_ids, history_dict, sensor_type
        )
        valid_24h_hours = [x for x in hourly_averages if x is not None]

        _LOGGER.debug(
            "[%s] Polling Analysis (%s) -> Timeline has %s/24 valid tracking points.",
            self.entry.title,
            sensor_type,
            len(valid_24h_hours),
        )

        if len(valid_24h_hours) >= 18:
            daily_avg_concentration = sum(valid_24h_hours) / len(valid_24h_hours)
            daily_aqi = calculate_aqi(
                daily_avg_concentration, AQI_CONFIGS.get(sensor_type)
            )
            daily_hours_remaining = 0
        else:
            daily_aqi = None
            daily_hours_remaining = estimate_hours_until_daily_valid(hourly_averages)

        (nowcast_aqi, nowcast_hours_remaining) = calculate_nowcast(
            sensor_type, hourly_averages, title=self.entry.title
        )

        return OutdoorMetrics(
            daily_aqi=daily_aqi,
            daily_hours_remaining=daily_hours_remaining,
            nowcast_aqi=nowcast_aqi,
            nowcast_hours_remaining=nowcast_hours_remaining,
        )
