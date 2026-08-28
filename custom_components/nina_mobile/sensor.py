"""Sensors for NINA Mobile."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    ATTR_ARS,
    ATTR_GPS_AVAILABLE,
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    ATTR_OUTSIDE_GERMANY,
    ATTR_TRACKER,
    ATTR_WARNING_COUNT,
)
from .coordinator import NinaMobileConfigEntry, WarningData
from .entity import NinaMobileEntity, NinaMobileWarningEntity

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class WarningSensorDescription(SensorEntityDescription):
    """Describe a diagnostic sensor derived from a warning."""

    value_fn: Callable[[WarningData], str | datetime | None]


WARNING_SENSOR_TYPES: tuple[WarningSensorDescription, ...] = (
    WarningSensorDescription(key="headline", name="Überschrift", value_fn=lambda w: w.headline),
    WarningSensorDescription(key="sender", name="Absender", value_fn=lambda w: w.sender),
    WarningSensorDescription(key="severity", name="Schweregrad", value_fn=lambda w: (w.severity or "unknown").lower()),
    WarningSensorDescription(key="affected_areas", name="Betroffene Gebiete", value_fn=lambda w: w.affected_areas),
    WarningSensorDescription(key="more_info_url", name="Weitere Informationen", value_fn=lambda w: w.more_info_url),
    WarningSensorDescription(
        key="sent",
        name="Gesendet",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_registry_enabled_default=False,
        value_fn=lambda w: w.sent,
    ),
    WarningSensorDescription(
        key="start",
        name="Beginn",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_registry_enabled_default=False,
        value_fn=lambda w: w.start,
    ),
    WarningSensorDescription(
        key="expires",
        name="Ablauf",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_registry_enabled_default=False,
        value_fn=lambda w: w.expires,
    ),
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: NinaMobileConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the region sensor and per-slot diagnostics."""
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = [NinaMobileRegionSensor(coordinator)]

    for slot in range(1, coordinator.message_slots + 1):
        entities.extend(
            NinaMobileWarningSensor(coordinator, slot, description)
            for description in WARNING_SENSOR_TYPES
        )

    async_add_entities(entities)


class NinaMobileRegionSensor(NinaMobileEntity, SensorEntity):
    """Current district selected from the GPS tracker."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator) -> None:
        """Initialize the region sensor."""
        super().__init__(coordinator)
        self._attr_name = "Aktuelle Warnregion"
        self._attr_unique_id = f"{coordinator.entry.entry_id}-region"

    @property
    def native_value(self) -> str | None:
        """Return the current district name."""
        if self.coordinator.data.region:
            return self.coordinator.data.region.name
        if self.coordinator.data.outside_germany:
            return "Außerhalb Deutschlands"
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return GPS/region diagnostics."""
        data = self.coordinator.data
        region = data.region
        return {
            ATTR_ARS: region.ars if region else None,
            ATTR_TRACKER: self.coordinator.tracker_entity_id,
            ATTR_GPS_AVAILABLE: data.gps_available,
            ATTR_LATITUDE: data.latitude,
            ATTR_LONGITUDE: data.longitude,
            ATTR_OUTSIDE_GERMANY: data.outside_germany,
            ATTR_WARNING_COUNT: sum(1 for warning in data.warnings if warning is not None),
        }


class NinaMobileWarningSensor(NinaMobileWarningEntity, SensorEntity):
    """Diagnostic sensor matching the structure of the normal NINA integration."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        coordinator,
        slot: int,
        description: WarningSensorDescription,
    ) -> None:
        """Initialize a warning diagnostic sensor."""
        super().__init__(coordinator, slot)
        self.entity_description = description
        self._attr_name = f"Warnung {slot} {description.name}"
        self._attr_unique_id = (
            f"{coordinator.entry.entry_id}-warning-{slot}-{description.key}"
        )

    @property
    def available(self) -> bool:
        """Only expose diagnostics while the slot contains a warning."""
        return self.warning() is not None and super().available

    @property
    def native_value(self) -> str | datetime | None:
        """Return the diagnostic value."""
        warning = self.warning()
        if warning is None:
            return None
        return self.entity_description.value_fn(warning)
