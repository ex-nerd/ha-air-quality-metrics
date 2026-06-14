"""Indoor IAQI tracking sensors."""

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.air_quality_metrics.const import DOMAIN
from custom_components.air_quality_metrics.metrics.epa.helpers import (
    get_aqi_attributes,
)
from custom_components.air_quality_metrics.metrics.epa.types import AQICategory
from custom_components.air_quality_metrics.sensors.indoor.coordinator import (
    IndoorDataCoordinator,
)
from custom_components.air_quality_metrics.sensors.svg import (
    generate_svg,
)

_LOGGER = logging.getLogger(__name__)


class BaseIAQISensor(CoordinatorEntity[IndoorDataCoordinator], SensorEntity):
    """Abstract base class to inherit shared DeviceInfo, unique IDs, and EPA lookup macros."""

    _attr_has_entity_name = True

    # Type declarations: Enforces static variable checks for static evaluation linting tools
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

    def __init__(self, coordinator: IndoorDataCoordinator, entry):
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
        aqi = self.coordinator.data.iaqi
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


class IAQISensor(BaseIAQISensor):
    """Atmotube IAQI."""

    _attr_translation_key = "iaqi"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_device_class = SensorDeviceClass.AQI
    _default_active_icon = "mdi:air-filter"

    @property
    def native_value(self) -> int | None:
        return self.coordinator.data.iaqi

    @property
    def entity_picture(self) -> str | None:
        epa_attrs = self._current_epa_attributes
        if not epa_attrs or not epa_attrs.color:
            return None
        return generate_svg(
            "mdi:air-filter",
            epa_attrs.color,
            f"IAQI: {self.native_value}" if self.native_value else None,
        )


class IAQIPrimaryPollutantSensor(BaseIAQISensor):
    """Exposes the worst recorded pollutant responsible for the IAQI value."""

    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "iaqi_primary_pollutant"
    _default_active_icon = "mdi:molecule"

    @property
    def native_value(self) -> str | None:
        if self.coordinator.data.iaqi is None:
            return None
        return self.coordinator.data.iaqi_primary

    @property
    def _default_active_icon(self) -> str | None:
        value = self.native_value
        if value == SensorDeviceClass.PM25 or value == SensorDeviceClass.PM10:
            return "mdi:blur"
        return "mdi:molecule"


class IAQICategorySensor(BaseIAQISensor):
    """
    Exposes the string code for the IAQI category name.

    These string codes should have corresponding values in the translation files.
    """

    _attr_translation_key = "iaqi_category"
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
            f"IAQI: {self.native_value}" if self.native_value else None,
        )


class IAQIColorSensor(BaseIAQISensor):
    """Exposes the hex color value for the current IAQI value."""

    _attr_entity_registry_enabled_default = False
    _attr_translation_key = "iaqi_color"
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
