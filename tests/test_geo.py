"""Dependency-free tests for the GeoJSON helpers."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

MODULE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "nina_mobile"
    / "geo.py"
)
spec = spec_from_file_location("nina_mobile_geo", MODULE_PATH)
assert spec and spec.loader
geo = module_from_spec(spec)
spec.loader.exec_module(geo)


def test_polygon_inside_outside_and_boundary() -> None:
    geometry = {
        "type": "Polygon",
        "coordinates": [
            [[7.0, 50.0], [8.0, 50.0], [8.0, 51.0], [7.0, 51.0], [7.0, 50.0]]
        ],
    }
    assert geo.point_in_geometry(7.5, 50.5, geometry)
    assert geo.point_in_geometry(7.0, 50.5, geometry)
    assert not geo.point_in_geometry(8.5, 50.5, geometry)


def test_polygon_hole() -> None:
    geometry = {
        "type": "Polygon",
        "coordinates": [
            [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]],
            [[4, 4], [6, 4], [6, 6], [4, 6], [4, 4]],
        ],
    }
    assert geo.point_in_geometry(2, 2, geometry)
    assert not geo.point_in_geometry(5, 5, geometry)


def test_multipolygon() -> None:
    geometry = {
        "type": "MultiPolygon",
        "coordinates": [
            [[[-2, -2], [-1, -2], [-1, -1], [-2, -1], [-2, -2]]],
            [[[1, 1], [2, 1], [2, 2], [1, 2], [1, 1]]],
        ],
    }
    assert geo.point_in_geometry(1.5, 1.5, geometry)
    assert not geo.point_in_geometry(0, 0, geometry)


def test_normalize_district_ars() -> None:
    assert geo.normalize_district_ars("053140000000") == "053140000000"
    assert geo.normalize_district_ars("05-314-1234567") == "053140000000"
