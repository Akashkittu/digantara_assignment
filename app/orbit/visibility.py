from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Tuple

from sgp4.api import jday


# WGS84 constants
_A = 6378137.0                 # semi-major axis (m)
_F = 1.0 / 298.257223563
_E2 = _F * (2.0 - _F)           # eccentricity^2


@dataclass(frozen=True)
class GroundStation:
    lat_deg: float
    lon_deg: float
    alt_m: float = 0.0


def gmst_rad(jd_ut1: float) -> float:
    """
    Approx GMST in radians.
    Good enough for visibility window / pass prediction (assignment level).
    """
    T = (jd_ut1 - 2451545.0) / 36525.0
    gmst_deg = (
        280.46061837
        + 360.98564736629 * (jd_ut1 - 2451545.0)
        + 0.000387933 * (T * T)
        - (T * T * T) / 38710000.0
    )
    gmst_deg = gmst_deg % 360.0
    return math.radians(gmst_deg)


def geodetic_to_ecef(gs: GroundStation) -> Tuple[float, float, float]:
    """
    Convert lat/lon/alt to ECEF (meters).
    """
    lat = math.radians(gs.lat_deg)
    lon = math.radians(gs.lon_deg)
    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)

    N = _A / math.sqrt(1.0 - _E2 * sin_lat * sin_lat)

    x = (N + gs.alt_m) * cos_lat * math.cos(lon)
    y = (N + gs.alt_m) * cos_lat * math.sin(lon)
    z = (N * (1.0 - _E2) + gs.alt_m) * sin_lat
    return (x, y, z)


def teme_to_ecef(r_km: Tuple[float, float, float], t: datetime) -> Tuple[float, float, float]:
    """
    Approx conversion: rotate TEME around Z by GMST.
    Output ECEF meters.
    """
    if t.tzinfo is None:
        raise ValueError("datetime must be timezone-aware (UTC)")
    t = t.astimezone(timezone.utc)

    jd, fr = jday(t.year, t.month, t.day, t.hour, t.minute, t.second + t.microsecond / 1e6)
    theta = gmst_rad(jd + fr)  # radians

    x_km, y_km, z_km = r_km
    c = math.cos(theta)
    s = math.sin(theta)

    # rotate: ECEF = Rz(theta) * TEME
    x = c * x_km + s * y_km
    y = -s * x_km + c * y_km
    z = z_km

    # km -> m
    return (x * 1000.0, y * 1000.0, z * 1000.0)


def ecef_to_enu(dx: float, dy: float, dz: float, gs: GroundStation) -> Tuple[float, float, float]:
    """
    Convert ECEF delta vector to ENU (meters) for a given ground station.
    """
    lat = math.radians(gs.lat_deg)
    lon = math.radians(gs.lon_deg)

    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)
    sin_lon = math.sin(lon)
    cos_lon = math.cos(lon)

    # ENU basis
    e = -sin_lon * dx + cos_lon * dy
    n = -sin_lat * cos_lon * dx - sin_lat * sin_lon * dy + cos_lat * dz
    u = cos_lat * cos_lon * dx + cos_lat * sin_lon * dy + sin_lat * dz
    return (e, n, u)


def elevation_deg(r_teme_km: Tuple[float, float, float], t: datetime, gs: GroundStation) -> float:
    """
    Elevation angle (degrees) of the satellite as seen from the ground station at time t.
    > 0 means above the horizon.
    """
    sx, sy, sz = geodetic_to_ecef(gs)
    px, py, pz = teme_to_ecef(r_teme_km, t)

    dx = px - sx
    dy = py - sy
    dz = pz - sz

    e, n, u = ecef_to_enu(dx, dy, dz, gs)
    horiz = math.sqrt(e * e + n * n)
    return math.degrees(math.atan2(u, horiz))
