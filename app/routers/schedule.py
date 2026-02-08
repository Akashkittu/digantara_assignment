from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Query
from psycopg.rows import dict_row

from app.db.conn import get_conn
from app.schedule.optimizer import (
    PassItem,
    best_non_overlapping_weighted,
    top_k_passes,
)

Metric = Literal["duration", "max_elev"]

router = APIRouter(prefix="/schedule", tags=["schedule"])


def parse_utc(s: str) -> datetime:
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def clip_row_to_window(row: dict, qstart: datetime, qend: datetime) -> Optional[PassItem]:
    s = max(row["start_ts"], qstart)
    e = min(row["end_ts"], qend)
    if e <= s:
        return None
    dur = int((e - s).total_seconds())
    if dur < 5:
        return None
    return PassItem(
        id=row["id"],
        satellite_id=row["satellite_id"],
        ground_station_id=row["ground_station_id"],
        start_ts=s,
        end_ts=e,
        duration_s=dur,
        max_elev_deg=float(row["max_elev_deg"]),
    )


def fetch_candidate_passes(gs_id: int, qstart: datetime, qend: datetime, satellite_id: int | None):
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            if satellite_id is None:
                cur.execute(
                    """
                    SELECT id, satellite_id, ground_station_id, start_ts, end_ts, duration_s, max_elev_deg
                    FROM passes
                    WHERE ground_station_id = %s
                      AND start_ts < %s
                      AND end_ts > %s
                    ORDER BY end_ts ASC
                    """,
                    (gs_id, qend, qstart),
                )
            else:
                cur.execute(
                    """
                    SELECT id, satellite_id, ground_station_id, start_ts, end_ts, duration_s, max_elev_deg
                    FROM passes
                    WHERE ground_station_id = %s
                      AND satellite_id = %s
                      AND start_ts < %s
                      AND end_ts > %s
                    ORDER BY end_ts ASC
                    """,
                    (gs_id, satellite_id, qend, qstart),
                )
            return cur.fetchall()


@router.get("/best")
def best_schedule(
    gs_id: int = Query(..., ge=1),
    start: str = Query(..., description="ISO datetime, e.g. 2026-02-08T06:00:00+00:00"),
    end: str = Query(..., description="ISO datetime"),
    metric: Metric = Query("duration"),
    satellite_id: Optional[int] = Query(None, ge=1, description="Optional filter by satellite_id"),
):
    qstart = parse_utc(start)
    qend = parse_utc(end)
    if qstart >= qend:
        return {"error": "start must be < end"}

    rows = fetch_candidate_passes(gs_id, qstart, qend, satellite_id)

    items = []
    for r in rows:
        p = clip_row_to_window(r, qstart, qend)
        if p:
            items.append(p)

    chosen, score = best_non_overlapping_weighted(items, metric=metric)

    return {
        "gs_id": gs_id,
        "satellite_id": satellite_id,
        "start": qstart.isoformat(),
        "end": qend.isoformat(),
        "metric": metric,
        "score": score,
        "count": len(chosen),
        "passes": [
            {
                "id": p.id,
                "satellite_id": p.satellite_id,
                "ground_station_id": p.ground_station_id,
                "start_ts": p.start_ts.isoformat(),
                "end_ts": p.end_ts.isoformat(),
                "duration_s": p.duration_s,
                "max_elev_deg": p.max_elev_deg,
            }
            for p in chosen
        ],
    }


@router.get("/top")
def top_schedule(
    gs_id: int = Query(..., ge=1),
    start: str = Query(...),
    end: str = Query(...),
    metric: Metric = Query("duration"),
    k: int = Query(5, ge=1, le=100),
    satellite_id: Optional[int] = Query(None, ge=1),
):
    qstart = parse_utc(start)
    qend = parse_utc(end)
    if qstart >= qend:
        return {"error": "start must be < end"}

    rows = fetch_candidate_passes(gs_id, qstart, qend, satellite_id)

    items = []
    for r in rows:
        p = clip_row_to_window(r, qstart, qend)
        if p:
            items.append(p)

    topk = top_k_passes(items, metric=metric, k=k)

    return {
        "gs_id": gs_id,
        "satellite_id": satellite_id,
        "start": qstart.isoformat(),
        "end": qend.isoformat(),
        "metric": metric,
        "k": k,
        "count": len(topk),
        "passes": [
            {
                "id": p.id,
                "satellite_id": p.satellite_id,
                "ground_station_id": p.ground_station_id,
                "start_ts": p.start_ts.isoformat(),
                "end_ts": p.end_ts.isoformat(),
                "duration_s": p.duration_s,
                "max_elev_deg": p.max_elev_deg,
            }
            for p in topk
        ],
    }
