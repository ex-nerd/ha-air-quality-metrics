"""Outdoor NowCast tracking sensors."""

import logging
from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from custom_components.air_quality_metrics.const import DOMAIN
from custom_components.air_quality_metrics.metrics.epa.helpers import (
    get_aqi_attributes,
)
from custom_components.air_quality_metrics.metrics.epa.types import AQICategory
from custom_components.air_quality_metrics.sensors.outdoor.coordinator import (
    OutdoorDataCoordinator,
)
from custom_components.air_quality_metrics.sensors.svg import (
    generate_svg,
)

_LOGGER = logging.getLogger(__name__)


class BaseNowCastSensor(CoordinatorEntity[OutdoorDataCoordinator], SensorEntity):
    """Abstract base class to inherit shared DeviceInfo, unique IDs, and EPA lookup macros."""

    _attr_has_entity_name = True

    _attr_translation_key: str
    _default_active_icon: str

    def __init_subclass__(cls, **kwargs):
        """Enforce that inheriting subclasses strictly configure necessary attributes."""
        super().__init_subclass__(**kwargs)

        # Guard rails to catch missing configurations at application startup
        if not hasattr(cls, "_attr_translation_key"):
            raise TypeError(f"Class {cls.__name__} must define '_attr_translation_key'")

        if not hasattr(cls, "_default_active_icon"):
            raise TypeError(f"Class {cls.__name__} must define '_default_active_icon'")

    def __init__(self, coordinator: OutdoorDataCoordinator, entry):
        """Initialize and auto-route identical device properties and namespace ids."""
        super().__init__(coordinator)

        # Pull the suffix directly from the translation key to guarantee zero unique ID collisions
        self._attr_unique_id = f"{entry.entry_id}_{self._attr_translation_key}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
        )

    @property
    def _current_epa_attributes(self) -> AQICategory | None:
        """Helper to safely fetch the active translation dataclass object across children."""
        aqi = self.coordinator.data.nowcast_aqi
        return get_aqi_attributes(aqi) if aqi is not None else None

    @property
    def icon(self) -> str:
        """Universal fallback clock icon when integration is fetching initial database history."""
        if self.native_value:
            return self._default_active_icon
        return "mdi:database-clock-outline"


# ==========================================
# Primary Metric & Dynamic Category Sensors
# ==========================================


class NowCastAQISensor(BaseNowCastSensor):
    """
    The 12-hour variation-weighted worst-case composite NowCast AQI.

    See https://en.wikipedia.org/wiki/NowCast_(air_quality_index)
    """

    _attr_translation_key = "nowcast_aqi"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_device_class = SensorDeviceClass.AQI
    _default_active_icon = "mdi:air-filter"

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.nowcast_aqi

    @property
    def entity_picture(self) -> str | None:
        epa_attrs = self._current_epa_attributes
        if not epa_attrs or not epa_attrs.color:
            return None
        return generate_svg(
            "mdi:air-filter",
            epa_attrs.color,
            f"NowCast: {self.native_value}" if self.native_value else None,
        )


class NowCastPrimaryPollutantSensor(BaseNowCastSensor):
    """Exposes the worst recorded pollutant responsible for the NowCast value."""

    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "nowcast_primary_pollutant"
    _default_active_icon = "mdi:molecule"

    @property
    def native_value(self) -> str | None:
        if self.coordinator.data.nowcast_aqi is None:
            return None
        return self.coordinator.data.nowcast_primary

    @property
    def _default_active_icon(self) -> str | None:
        value = self.native_value
        if value == SensorDeviceClass.PM25 or value == SensorDeviceClass.PM10:
            return "mdi:blur"
        return "mdi:molecule"


class NowCastCategorySensor(BaseNowCastSensor):
    """
    Exposes the string code for the NowCast category name.

    These string codes should have corresponding values in the translation files.
    """

    _attr_translation_key = "nowcast_category"
    _default_active_icon = "mdi:label-outline"

    @property
    def native_value(self) -> str | None:
        epa_attrs = self._current_epa_attributes
        return epa_attrs.category if epa_attrs else None

    @property
    def entity_picture(self) -> str | None:
        epa_attrs = self._current_epa_attributes
        if not epa_attrs or not epa_attrs.color:
            return None
        return generate_svg(
            "mdi:label",
            epa_attrs.color,
            f"NowCast: {self.native_value}" if self.native_value else None,
        )


# ==========================================
# EPA Theme / Color Metric Sensors
# ==========================================


class NowCastColorSensor(BaseNowCastSensor):
    """Exposes the hex color value for the current NowCast value."""

    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "nowcast_color"
    _default_active_icon = "mdi:palette-outline"

    @property
    def native_value(self) -> str | None:
        epa_attrs = self._current_epa_attributes
        return epa_attrs.color if epa_attrs else None

    @property
    def entity_picture(self) -> str | None:
        return (
            generate_svg("mdi:palette-outline", self.native_value)
            if self.native_value
            else None
        )


class NowCastColorAssistSensor(BaseNowCastSensor):
    """Exposes the ColorVision Assist hex color value for the current NowCast value."""

    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "nowcast_color_assist"
    _default_active_icon = "mdi:palette-outline"

    @property
    def native_value(self) -> str | None:
        epa_attrs = self._current_epa_attributes
        return epa_attrs.color_assist if epa_attrs else None

    @property
    def entity_picture(self) -> str | None:
        return (
            generate_svg("mdi:palette-outline", self.native_value)
            if self.native_value
            else None
        )


class NowCastColorNameSensor(BaseNowCastSensor):
    """
    Exposes the name string for the EPA color value for the current NowCast.

    These string codes should have corresponding values in the translation files.
    """

    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "nowcast_color_name"
    _default_active_icon = "mdi:palette-outline"

    @property
    def native_value(self) -> str | None:
        epa_attrs = self._current_epa_attributes
        return epa_attrs.color_name if epa_attrs else None

    @property
    def entity_picture(self) -> str | None:
        epa_attrs = self._current_epa_attributes
        return (
            generate_svg("mdi:palette-outline", epa_attrs.color) if epa_attrs else None
        )


# ==========================================
# Diagnostics & Flow Timing
# ==========================================


class NowCastStatusSensor(
    CoordinatorEntity[OutdoorDataCoordinator], RestoreEntity, SensorEntity
):
    """Exposes the estimated time when NowCast data will become available."""

    _attr_has_entity_name = True
    _attr_translation_key = "nowcast_data_expected"
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(self, coordinator: OutdoorDataCoordinator, entry):
        """Initialize the pipeline status tracker entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_nowcast_status"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
        )

    async def async_added_to_hass(self) -> None:
        """Handle component restoration from underlying JSON core storage."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) is not None:
            if last_state.state not in (None, "unknown", "unavailable"):
                try:
                    restored_time = dt_util.parse_datetime(last_state.state)
                    if restored_time and (
                        self.coordinator.data is None
                        or self.coordinator.data.nowcast_available_at is None
                    ):
                        _LOGGER.debug(
                            "[%s] Restoring persistent NowCast activation stamp: %s",
                            self.entity_id,
                            last_state.state,
                        )
                        self.coordinator.async_initialize_restored_timestamps(
                            nowcast_activated_at=restored_time
                        )
                except Exception as err:
                    _LOGGER.error(
                        "[%s] Restoration parsing failure: %s", self.entity_id, err
                    )

    @property
    def native_value(self) -> datetime | None:
        """Return the exact datetime object when NowCast data is expected."""
        if self.coordinator.data.nowcast_aqi is None:
            return self.coordinator.data.nowcast_available_at
        if self.coordinator.data.nowcast_activated_at:
            return min(self.coordinator.data.nowcast_activated_at, dt_util.utcnow())
        return None

    @property
    def icon(self) -> str:
        if self.coordinator.data.nowcast_aqi is not None:
            return "mdi:clock-check-outline"
        return "mdi:database-clock-outline"
