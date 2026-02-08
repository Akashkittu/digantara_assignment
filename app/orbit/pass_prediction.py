from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Tuple

from sgp4.api import Satrec, jday

from app.orbit.visibility import GroundStation, elevation_deg


@dataclass(frozen=True)
class PassWindow:
    start_ts: datetime
    end_ts: datetime
    duration_s: int
    max_elev_deg: float


class PassPredictionError(RuntimeError):
    pass


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("datetime must be timezone-aware (UTC)")
    return dt.astimezone(timezone.utc)


def _r_km_at(sat: Satrec, t: datetime) -> Tuple[float, float, float]:
    t = _to_utc(t)
    jd, fr = jday(t.year, t.month, t.day, t.hour, t.minute, t.second + t.microsecond / 1e6)
    err, r, _v = sat.sgp4(jd, fr)
    if err != 0:
        raise PassPredictionError(f"SGP4 error code={err} at {t.isoformat()}")
    return (r[0], r[1], r[2])


def _elev_at(sat: Satrec, gs: GroundStation, t: datetime) -> float:
    r_km = _r_km_at(sat, t)
    return elevation_deg(r_km, t, gs)


def _bisect_crossing(
    sat: Satrec,
    gs: GroundStation,
    t0: datetime,
    t1: datetime,
    elev0: float,
    elev1: float,
    cutoff_deg: float,
    iters: int = 25,
) -> datetime:
    """
    Find approximate time when elevation crosses cutoff between (t0,t1).
    Assumes elev0 and elev1 are on opposite sides of cutoff.
    """
    lo = _to_utc(t0)
    hi = _to_utc(t1)
    elo = elev0
    ehi = elev1

    for _ in range(iters):
        mid = lo + (hi - lo) / 2
        emid = _elev_at(sat, gs, mid)

        # Keep interval that still brackets the cutoff crossing
        if (elo - cutoff_deg) * (emid - cutoff_deg) <= 0:
            hi, ehi = mid, emid
        else:
            lo, elo = mid, emid

    return lo + (hi - lo) / 2


def predict_passes(
    line1: str,
    line2: str,
    gs: GroundStation,
    start: datetime,
    end: datetime,
    step_seconds: int = 30,
    cutoff_deg: float = 0.0,
    min_duration_s: int = 5,
) -> List[PassWindow]:
    """
    Coarse scan at step_seconds, then refine rise/set using bisection.
    """
    start = _to_utc(start)
    end = _to_utc(end)
    if start >= end:
        raise ValueError("start must be < end")

    sat = Satrec.twoline2rv(line1, line2)

    step = timedelta(seconds=step_seconds)
    times: List[datetime] = []
    t = start
    while t <= end:
        times.append(t)
        t += step

    passes: List[PassWindow] = []
    in_pass = False
    pass_start: datetime | None = None
    max_elev = -1e9

    prev_t = None
    prev_el = None

    for cur_t in times:
        cur_el = _elev_at(sat, gs, cur_t)

        if prev_t is not None and prev_el is not None:
            # entering: prev <= cutoff and cur > cutoff
            if (not in_pass) and (prev_el <= cutoff_deg) and (cur_el > cutoff_deg):
                refined_start = _bisect_crossing(
                    sat, gs, prev_t, cur_t, prev_el, cur_el, cutoff_deg
                )
                in_pass = True
                pass_start = refined_start
                max_elev = cur_el

            # while inside pass
            if in_pass:
                if cur_el > max_elev:
                    max_elev = cur_el

                # exiting: prev > cutoff and cur <= cutoff
                if (prev_el > cutoff_deg) and (cur_el <= cutoff_deg):
                    refined_end = _bisect_crossing(
                        sat, gs, prev_t, cur_t, prev_el, cur_el, cutoff_deg
                    )
                    if pass_start is not None:
                        dur = (refined_end - pass_start).total_seconds()
                        if dur >= min_duration_s:
                            passes.append(
                                PassWindow(
                                    start_ts=pass_start,
                                    end_ts=refined_end,
                                    duration_s=int(round(dur)),
                                    max_elev_deg=float(max_elev),
                                )
                            )
                    in_pass = False
                    pass_start = None
                    max_elev = -1e9

        prev_t = cur_t
        prev_el = cur_el

    return passes
