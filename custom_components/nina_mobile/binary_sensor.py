"""Binary sensors for NINA Mobile warning slots."""

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    ATTR_AFFECTED_AREAS,
    ATTR_ARS,
    ATTR_DESCRIPTION,
    ATTR_EXPIRES,
    ATTR_HEADLINE,
    ATTR_ID,
    ATTR_MORE_INFO_URL,
    ATTR_WEB,
    ATTR_RECOMMENDED_ACTIONS,
    ATTR_REGION,
    ATTR_SENDER,
    ATTR_SENT,
    ATTR_SEVERITY,
    ATTR_START,
    ATTR_WARNING_ID,
)
from .coordinator import NinaMobileConfigEntry
from .entity import NinaMobileWarningEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: NinaMobileConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up fixed warning slots."""
    coordinator = entry.runtime_data
    async_add_entities(
        NinaMobileWarningBinarySensor(coordinator, slot)
        for slot in range(1, coordinator.message_slots + 1)
    )


class NinaMobileWarningBinarySensor(NinaMobileWarningEntity, BinarySensorEntity):
    """One stable NINA Mobile warning slot."""

    _attr_device_class = BinarySensorDeviceClass.SAFETY

    def __init__(self, coordinator, slot: int) -> None:
        """Initialize the warning slot."""
        super().__init__(coordinator, slot)
        self._attr_name = f"Warnung {slot}"
        self._attr_unique_id = f"{coordinator.entry.entry_id}-warning-{slot}"

    @property
    def is_on(self) -> bool:
        """Return True while this slot contains a valid warning."""
        warning = self.warning()
        return bool(warning and warning.is_valid)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the warning details for consumers such as other integrations."""
        warning = self.warning()
        if warning is None:
            return {}

        region = self.coordinator.data.region
        return {
            ATTR_WARNING_ID: warning.id,
            ATTR_ID: warning.id,
            ATTR_HEADLINE: warning.headline,
            ATTR_DESCRIPTION: warning.description,
            ATTR_SENDER: warning.sender,
            ATTR_SEVERITY: warning.severity or "Unknown",
            ATTR_RECOMMENDED_ACTIONS: warning.recommended_actions,
            ATTR_AFFECTED_AREAS: warning.affected_areas,
            ATTR_MORE_INFO_URL: warning.more_info_url,
            ATTR_WEB: warning.more_info_url,
            ATTR_SENT: warning.sent.isoformat() if warning.sent else None,
            ATTR_START: warning.start.isoformat() if warning.start else None,
            ATTR_EXPIRES: warning.expires.isoformat() if warning.expires else None,
            ATTR_ARS: region.ars if region else None,
            ATTR_REGION: region.name if region else None,
        }
