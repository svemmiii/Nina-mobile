"""Data coordinator for NINA Mobile."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
import logging

import aiohttp
from typing import Any

from pynina import ApiError, Nina

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    BKG_BBOX_EPSILON,
    BKG_WFS_TYPENAME,
    BKG_WFS_URL,
    CONF_MESSAGE_SLOTS,
    CONF_TRACKER,
    DOMAIN,
    SCAN_INTERVAL,
)
from .geo import normalize_district_ars, point_in_geometry

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True, frozen=True)
class RegionInfo:
    """Current administrative district."""

    ars: str
    name: str
    designation: str
    geometry: dict[str, Any]


@dataclass(slots=True, frozen=True)
class WarningData:
    """Normalized NINA warning data."""

    id: str
    headline: str
    description: str
    sender: str
    severity: str | None
    recommended_actions: str
    affected_areas: str
    more_info_url: str
    sent: datetime | None
    start: datetime | None
    expires: datetime | None
    is_valid: bool


@dataclass(slots=True, frozen=True)
class NinaMobileData:
    """Coordinator payload exposed to entities."""

    region: RegionInfo | None
    warnings: tuple[WarningData | None, ...]
    gps_available: bool
    outside_germany: bool
    latitude: float | None = field(compare=False)
    longitude: float | None = field(compare=False)


class RegionLookupError(Exception):
    """Raised when the BKG district lookup fails."""


class NinaMobileCoordinator(DataUpdateCoordinator[NinaMobileData]):
    """Coordinate GPS region resolution and NINA polling."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self.tracker_entity_id: str = entry.data[CONF_TRACKER]
        self.message_slots: int = int(entry.data[CONF_MESSAGE_SLOTS])
        self._session = async_get_clientsession(hass)
        self._region: RegionInfo | None = None
        self._outside_germany = False
        self._nina: Nina | None = None
        self._last_latitude: float | None = None
        self._last_longitude: float | None = None
        self._gps_available = False
        self._tracker_unsubscribe = None
        self._region_lock = asyncio.Lock()

        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=SCAN_INTERVAL,
            always_update=False,
        )

    def async_start_tracking(self) -> None:
        """Listen for GPS tracker changes."""
        if self._tracker_unsubscribe is not None:
            return

        self._tracker_unsubscribe = async_track_state_change_event(
            self.hass,
            [self.tracker_entity_id],
            self._async_tracker_state_changed,
        )

    @callback
    def async_stop_tracking(self) -> None:
        """Stop listening for GPS tracker changes."""
        if self._tracker_unsubscribe is not None:
            self._tracker_unsubscribe()
            self._tracker_unsubscribe = None

    @callback
    def _async_tracker_state_changed(self, event: Event) -> None:
        """Handle a tracker state change without touching warning entities unnecessarily."""
        new_state: State | None = event.data.get("new_state")
        coordinates = self._coordinates_from_state(new_state)
        if coordinates is None:
            self._gps_available = False
            return

        latitude, longitude = coordinates
        self._gps_available = True
        self._last_latitude = latitude
        self._last_longitude = longitude

        if self._region and point_in_geometry(longitude, latitude, self._region.geometry):
            return

        self.hass.async_create_task(
            self._async_handle_possible_region_change(latitude, longitude)
        )

    async def _async_handle_possible_region_change(
        self, latitude: float, longitude: float
    ) -> None:
        """Resolve a district only when the point has left the cached polygon."""
        async with self._region_lock:
            if self._region and point_in_geometry(
                longitude, latitude, self._region.geometry
            ):
                return

            previous_ars = self._region.ars if self._region else None
            previous_outside = self._outside_germany

            try:
                new_region = await self._async_resolve_region(latitude, longitude)
            except RegionLookupError as err:
                LOGGER.warning("Could not resolve NINA Mobile region: %s", err)
                return

            self._set_region(new_region)

            new_ars = self._region.ars if self._region else None
            if previous_ars != new_ars or previous_outside != self._outside_germany:
                await self.async_refresh()

    async def _async_update_data(self) -> NinaMobileData:
        """Refresh the current region if needed and then poll NINA."""
        state = self.hass.states.get(self.tracker_entity_id)
        coordinates = self._coordinates_from_state(state)

        if coordinates is not None:
            latitude, longitude = coordinates
            self._gps_available = True
            self._last_latitude = latitude
            self._last_longitude = longitude

            if not self._region or not point_in_geometry(
                longitude, latitude, self._region.geometry
            ):
                try:
                    region = await self._async_resolve_region(latitude, longitude)
                except RegionLookupError as err:
                    if self._region is None:
                        raise UpdateFailed(str(err)) from err
                    LOGGER.warning(
                        "Region lookup failed; keeping previous district %s: %s",
                        self._region.ars,
                        err,
                    )
                else:
                    self._set_region(region)
        else:
            self._gps_available = False

        if self._region is None:
            return NinaMobileData(
                region=None,
                warnings=self._assign_warning_slots([]),
                gps_available=self._gps_available,
                outside_germany=self._outside_germany,
                latitude=self._last_latitude,
                longitude=self._last_longitude,
            )

        if self._nina is None:
            self._nina = Nina(self._session)
            self._nina.add_region(self._region.ars)

        try:
            async with asyncio.timeout(15):
                await self._nina.update()
        except (ApiError, TimeoutError) as err:
            raise UpdateFailed(f"NINA update failed: {err}") from err

        warnings = self._parse_warnings(self._region.ars)
        return NinaMobileData(
            region=self._region,
            warnings=self._assign_warning_slots(warnings),
            gps_available=self._gps_available,
            outside_germany=False,
            latitude=self._last_latitude,
            longitude=self._last_longitude,
        )

    def _set_region(self, region: RegionInfo | None) -> None:
        """Set a district and rebuild pynina only when the ARS changes."""
        old_ars = self._region.ars if self._region else None
        new_ars = region.ars if region else None

        self._region = region
        self._outside_germany = region is None

        if old_ars == new_ars:
            return

        if region is None:
            self._nina = None
            return

        self._nina = Nina(self._session)
        self._nina.add_region(region.ars)
        LOGGER.info("NINA Mobile region changed to %s (%s)", region.name, region.ars)

    async def _async_resolve_region(
        self, latitude: float, longitude: float
    ) -> RegionInfo | None:
        """Resolve a GPS point to a district using the public BKG VG250 WFS."""
        epsilon = BKG_BBOX_EPSILON
        base_params = {
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "BBOX": (
                f"{longitude - epsilon},{latitude - epsilon},"
                f"{longitude + epsilon},{latitude + epsilon},EPSG:4326"
            ),
            "SRSNAME": "EPSG:4326",
            "outputFormat": "application/json",
            "count": "5",
        }

        features: list[Any] = []
        last_error: RegionLookupError | None = None
        # BKG examples use the unprefixed layer name. Some WFS clients/servers
        # prefer the namespace-prefixed form, so try both before treating an
        # empty result as "outside Germany".
        for typename in (BKG_WFS_TYPENAME, f"vg250:{BKG_WFS_TYPENAME}"):
            params = {**base_params, "TYPENAMES": typename}
            try:
                async with asyncio.timeout(15):
                    response = await self._session.get(BKG_WFS_URL, params=params)
                    if response.status != 200:
                        text = await response.text()
                        last_error = RegionLookupError(
                            f"BKG WFS returned HTTP {response.status}: {text[:160]}"
                        )
                        continue
                    payload = await response.json(content_type=None)
            except (TimeoutError, OSError, aiohttp.ClientError) as err:
                last_error = RegionLookupError(f"BKG WFS request failed: {err}")
                continue
            except ValueError as err:
                last_error = RegionLookupError("BKG WFS returned invalid JSON")
                continue

            candidate_features = (
                payload.get("features", []) if isinstance(payload, dict) else []
            )
            if not isinstance(candidate_features, list):
                last_error = RegionLookupError("BKG WFS response has no feature list")
                continue
            if candidate_features:
                features = candidate_features
                break

        if not features:
            if last_error is not None:
                raise last_error
            return None

        selected: dict[str, Any] | None = None
        for feature in features:
            if not isinstance(feature, dict):
                continue
            if point_in_geometry(longitude, latitude, feature.get("geometry")):
                selected = feature
                break

        if selected is None:
            selected = next((f for f in features if isinstance(f, dict)), None)
        if selected is None:
            return None

        properties = selected.get("properties", {})
        if not isinstance(properties, dict):
            raise RegionLookupError("BKG WFS feature has no properties")

        ars = normalize_district_ars(
            properties.get("ARS")
            or properties.get("ars")
            or properties.get("RS")
            or properties.get("rs")
        )
        if ars is None:
            raise RegionLookupError("BKG WFS feature contains no usable ARS")

        name = str(properties.get("GEN") or properties.get("gen") or ars)
        designation = str(properties.get("BEZ") or properties.get("bez") or "")
        geometry = selected.get("geometry")
        if not isinstance(geometry, dict):
            raise RegionLookupError("BKG WFS feature contains no geometry")

        return RegionInfo(
            ars=ars,
            name=name,
            designation=designation,
            geometry=geometry,
        )

    def _parse_warnings(self, ars: str) -> list[WarningData]:
        """Convert pynina warning objects into stable Home Assistant data."""
        if self._nina is None:
            return []

        raw_warnings = self._nina.warnings.get(ars, [])
        result: list[WarningData] = []
        seen: set[tuple[str, str]] = set()

        for raw in raw_warnings:
            headline = str(getattr(raw, "headline", "") or "")
            expires_raw = getattr(raw, "expires", None)
            duplicate_key = (headline, str(expires_raw or ""))
            if duplicate_key in seen:
                continue
            seen.add(duplicate_key)

            severity_raw = getattr(raw, "severity", None)
            severity = str(severity_raw) if severity_raw else None
            if severity and severity.lower() == "unknown":
                severity = None

            affected_areas = ", ".join(
                str(area) for area in (getattr(raw, "affected_areas", None) or [])
            )
            actions = " ".join(
                str(action)
                for action in (getattr(raw, "recommended_actions", None) or [])
            )

            result.append(
                WarningData(
                    id=str(getattr(raw, "id", "") or ""),
                    headline=headline,
                    description=str(getattr(raw, "description", "") or ""),
                    sender=str(getattr(raw, "sender", "") or ""),
                    severity=severity,
                    recommended_actions=actions,
                    affected_areas=affected_areas,
                    more_info_url=str(getattr(raw, "web", "") or ""),
                    sent=self._parse_datetime(getattr(raw, "sent", None)),
                    start=self._parse_datetime(getattr(raw, "start", None)),
                    expires=self._parse_datetime(expires_raw),
                    is_valid=bool(getattr(raw, "is_valid", True)),
                )
            )

        return result

    def _assign_warning_slots(
        self, warnings: list[WarningData]
    ) -> tuple[WarningData | None, ...]:
        """Keep warning IDs in the same slot across refreshes whenever possible."""
        slots: list[WarningData | None] = [None] * self.message_slots
        by_id = {warning.id: warning for warning in warnings if warning.id}
        used_ids: set[str] = set()

        previous = self.data.warnings if self.data is not None else ()
        for index, previous_warning in enumerate(previous[: self.message_slots]):
            if previous_warning is None:
                continue
            current = by_id.get(previous_warning.id)
            if current is None:
                continue
            slots[index] = current
            used_ids.add(current.id)

        remaining = [warning for warning in warnings if warning.id not in used_ids]
        remaining_iter = iter(remaining)
        for index, slot in enumerate(slots):
            if slot is not None:
                continue
            try:
                slots[index] = next(remaining_iter)
            except StopIteration:
                break

        return tuple(slots)

    @staticmethod
    def _parse_datetime(value: object) -> datetime | None:
        """Parse an ISO timestamp from pynina."""
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value))
        except ValueError:
            return None

    @staticmethod
    def _coordinates_from_state(state: State | None) -> tuple[float, float] | None:
        """Extract latitude/longitude from a Home Assistant device_tracker state."""
        if state is None:
            return None

        latitude = state.attributes.get("latitude")
        longitude = state.attributes.get("longitude")
        if latitude is None or longitude is None:
            return None

        try:
            return float(latitude), float(longitude)
        except (TypeError, ValueError):
            return None


NinaMobileConfigEntry = ConfigEntry[NinaMobileCoordinator]
