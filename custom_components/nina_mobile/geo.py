"""Small GeoJSON helpers used by NINA Mobile.

The implementation is intentionally dependency free. We only need point-in-polygon
checks for the current district geometry returned by the BKG WFS service.
"""

from __future__ import annotations

from typing import Any

_EPSILON = 1e-10


def _point_on_segment(
    x: float,
    y: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
) -> bool:
    """Return True when a point lies on a line segment."""
    cross = (y - y1) * (x2 - x1) - (x - x1) * (y2 - y1)
    if abs(cross) > _EPSILON:
        return False

    return (
        min(x1, x2) - _EPSILON <= x <= max(x1, x2) + _EPSILON
        and min(y1, y2) - _EPSILON <= y <= max(y1, y2) + _EPSILON
    )


def point_in_ring(lon: float, lat: float, ring: list[list[float]]) -> bool:
    """Return True if a lon/lat point is inside or on the boundary of a ring."""
    if len(ring) < 3:
        return False

    inside = False
    j = len(ring) - 1

    for i, current in enumerate(ring):
        previous = ring[j]
        x1, y1 = float(previous[0]), float(previous[1])
        x2, y2 = float(current[0]), float(current[1])

        if _point_on_segment(lon, lat, x1, y1, x2, y2):
            return True

        if (y2 > lat) != (y1 > lat):
            x_intersection = (x1 - x2) * (lat - y2) / (y1 - y2) + x2
            if lon < x_intersection:
                inside = not inside

        j = i

    return inside


def point_in_polygon(lon: float, lat: float, polygon: list[list[list[float]]]) -> bool:
    """Return True if a point is inside a GeoJSON polygon including its holes."""
    if not polygon or not point_in_ring(lon, lat, polygon[0]):
        return False

    return not any(point_in_ring(lon, lat, hole) for hole in polygon[1:])


def point_in_geometry(lon: float, lat: float, geometry: dict[str, Any] | None) -> bool:
    """Return True if a point is inside a Polygon or MultiPolygon GeoJSON geometry."""
    if not geometry:
        return False

    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")

    if geometry_type == "Polygon" and isinstance(coordinates, list):
        return point_in_polygon(lon, lat, coordinates)

    if geometry_type == "MultiPolygon" and isinstance(coordinates, list):
        return any(point_in_polygon(lon, lat, polygon) for polygon in coordinates)

    return False


def normalize_district_ars(value: object) -> str | None:
    """Normalize an ARS/RS value to the 12-digit NINA district ARS."""
    if value is None:
        return None

    digits = "".join(character for character in str(value) if character.isdigit())
    if not digits:
        return None

    digits = digits.zfill(12)
    if len(digits) < 5:
        return None

    return f"{digits[:5]}0000000"
