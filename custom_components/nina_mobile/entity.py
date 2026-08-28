"""Base entity for NINA Mobile."""

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NinaMobileCoordinator, WarningData


class NinaMobileEntity(CoordinatorEntity[NinaMobileCoordinator]):
    """Base entity shared by all NINA Mobile entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: NinaMobileCoordinator) -> None:
        """Initialize the base entity."""
        super().__init__(coordinator)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name=coordinator.entry.title,
            manufacturer="NINA / BBK (data source)",
            entry_type=DeviceEntryType.SERVICE,
        )


class NinaMobileWarningEntity(NinaMobileEntity):
    """Base entity bound to one stable warning slot."""

    def __init__(self, coordinator: NinaMobileCoordinator, slot: int) -> None:
        """Initialize a warning-slot entity."""
        super().__init__(coordinator)
        self.slot = slot
        self.warning_index = slot - 1

    def warning(self) -> WarningData | None:
        """Return the warning currently assigned to this slot."""
        if self.warning_index >= len(self.coordinator.data.warnings):
            return None
        return self.coordinator.data.warnings[self.warning_index]
