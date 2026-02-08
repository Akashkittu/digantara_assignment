from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, List, Tuple

from sgp4.api import Satrec, jday


@dataclass(frozen=True)
class Sgp4State:
    t: datetime           # UTC datetime
    r_km: Tuple[float, float, float]   # position in km (TEME)
    v_km_s: Tuple[float, float, float] # velocity in km/s (TEME)


class Sgp4PropagationError(RuntimeError):
    pass


def _to_jd(dt: datetime) -> tuple[float, float]:
    if dt.tzinfo is None:
        raise ValueError("datetime must be timezone-aware (UTC).")
    dt = dt.astimezone(timezone.utc)
    return jday(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second + dt.microsecond / 1e6)


def propagate_tle(line1: str, line2: str, times: Iterable[datetime]) -> List[Sgp4State]:
    """
    Propagate a single TLE at given UTC datetimes.
    Returns TEME r,v.
    """
    sat = Satrec.twoline2rv(line1, line2)
    out: List[Sgp4State] = []

    for t in times:
        jd, fr = _to_jd(t)
        err, r, v = sat.sgp4(jd, fr)
        if err != 0:
            # We keep it simple: fail fast. Later we can log + skip bad points if needed.
            raise Sgp4PropagationError(f"SGP4 error code={err} at t={t.isoformat()}")
        out.append(Sgp4State(t=t, r_km=(r[0], r[1], r[2]), v_km_s=(v[0], v[1], v[2])))

    return out
