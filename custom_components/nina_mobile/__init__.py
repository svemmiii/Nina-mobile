"""NINA Mobile integration."""

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .coordinator import NinaMobileConfigEntry, NinaMobileCoordinator

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(
    hass: HomeAssistant, entry: NinaMobileConfigEntry
) -> bool:
    """Set up NINA Mobile from a config entry."""
    coordinator = NinaMobileCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    coordinator.async_start_tracking()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: NinaMobileConfigEntry
) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        entry.runtime_data.async_stop_tracking()
    return unloaded
