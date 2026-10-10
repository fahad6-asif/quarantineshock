"""Quarantine zones: circles of the official radius around detections, unioned.

Buffers are computed in a metric projection (UTM 11N, EPSG:32611) so miles are real miles.
"""
from __future__ import annotations

from functools import lru_cache

from pyproj import Transformer
from shapely.geometry import Point, mapping, shape
from shapely.ops import transform, unary_union

METERS_PER_MILE = 1609.344
SQM_PER_SQMI = METERS_PER_MILE ** 2
UTM = "EPSG:32611"


@lru_cache(maxsize=1)
def _fwd():
    return Transformer.from_crs("EPSG:4326", UTM, always_xy=True).transform


@lru_cache(maxsize=1)
def _inv():
    return Transformer.from_crs(UTM, "EPSG:4326", always_xy=True).transform


def to_utm(geom):
    return transform(_fwd(), geom)


def to_wgs(geom):
    return transform(_inv(), geom)


def circle_utm(lat: float, lon: float, miles: float):
    return to_utm(Point(lon, lat)).buffer(miles * METERS_PER_MILE, quad_segs=64)


def build_zone_utm(points: list[tuple[float, float]], miles: float):
    """points = [(lat, lon), ...] -> union polygon in UTM meters."""
    return unary_union([circle_utm(lat, lon, miles) for lat, lon in points])


def area_sq_mi(geom_utm) -> float:
    return geom_utm.area / SQM_PER_SQMI


def to_geojson(geom_utm) -> dict:
    g = to_wgs(geom_utm).simplify(0.00005)
    return mapping(g)


def from_geojson(gj: dict):
    """GeoJSON (WGS84) -> UTM geometry."""
    return to_utm(shape(gj))


def contains(geom_utm, lat: float, lon: float) -> bool:
    return geom_utm.covers(to_utm(Point(lon, lat)))


def distance_to_edge_mi(geom_utm, lat: float, lon: float) -> float:
    """Positive = inside (distance to boundary), negative = outside (distance to zone)."""
    p = to_utm(Point(lon, lat))
    d = geom_utm.boundary.distance(p) / METERS_PER_MILE
    return d if geom_utm.covers(p) else -d
