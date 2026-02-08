from dotenv import load_dotenv

# ✅ Load .env BEFORE importing anything that reads env vars
load_dotenv()

import logging
from datetime import datetime, timezone

import psycopg
from psycopg import OperationalError, IntegrityError, DataError, ProgrammingError, InterfaceError
from psycopg.rows import dict_row

from fastapi import FastAPI, Request, Query, status, HTTPException
from fastapi.responses import JSONResponse

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.db.conn import check_db, get_conn
from app.schedule.optimizer import PassItem, best_non_overlapping_weighted, top_k_passes


app = FastAPI(title="Digantara Ground Pass Prediction", version="0.1.0")

# Rate limiting (in-memory for now)
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

logger = logging.getLogger("uvicorn.error")


def map_db_error(exc: Exception):
    # Don’t expose raw SQL or internal details to users
    if isinstance(exc, (OperationalError, InterfaceError)):
        return status.HTTP_503_SERVICE_UNAVAILABLE, "db_unavailable", "Database is unavailable. Try again."
    if isinstance(exc, DataError):
        return status.HTTP_400_BAD_REQUEST, "bad_query_params", "Invalid query parameters."
    if isinstance(exc, IntegrityError):
        return status.HTTP_409_CONFLICT, "db_conflict", "Database constraint conflict."
    if isinstance(exc, ProgrammingError):
        return status.HTTP_500_INTERNAL_SERVER_ERROR, "db_query_error", "Database query failed."
    return status.HTTP_500_INTERNAL_SERVER_ERROR, "db_error", "Database error."


# ✅ Global handler for psycopg DB errors
@app.exception_handler(psycopg.Error)
async def psycopg_exception_handler(request: Request, exc: psycopg.Error):
    logger.exception("DB error: %s", exc)  # full details only in server logs
    http_status, code, msg = map_db_error(exc)
    return JSONResponse(status_code=http_status, content={"error": code, "message": msg})


# Global fallback error handler (non-DB)
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "message": "Something went wrong."},
    )


@app.get("/health")
@limiter.limit("60/minute")
def health(request: Request):
    return {"status": "ok"}


@app.get("/")
@limiter.limit("60/minute")
def root(request: Request):
    return {"service": "ground-pass-prediction", "status": "running"}


@app.get("/db/health")
@limiter.limit("30/minute")
def db_health(request: Request):
    # If DB is down, psycopg error handler will return clean 503 JSON
    check_db()
    return {"db": "ok"}


# ✅ List all ground stations
@app.get("/ground-stations")
@limiter.limit("60/minute")
def get_ground_stations(
    request: Request,
    limit: int = Query(200, ge=1, le=500),
):
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, code, name, lat, lon, alt_m
                FROM ground_stations
                ORDER BY code
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()

    return {"count": len(rows), "items": rows}


@app.get("/passes")
@limiter.limit("60/minute")
def get_passes(
    request: Request,
    gs_id: int = Query(..., ge=1),
    start: datetime = Query(...),
    end: datetime = Query(...),
    limit: int = Query(200, ge=1, le=1000),
):
    # ✅ Guard: invalid time range
    if start >= end:
        raise HTTPException(
            status_code=400,
            detail="Invalid time window: 'start' must be strictly earlier than 'end'.",
        )

    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # ✅ Overlap logic:
            # pass overlaps window if pass.start < window.end AND pass.end > window.start
            cur.execute(
                """
                SELECT id, satellite_id, ground_station_id, start_ts, end_ts, duration_s, max_elev_deg
                FROM passes
                WHERE ground_station_id = %s
                  AND start_ts < %s
                  AND end_ts > %s
                ORDER BY start_ts
                LIMIT %s
                """,
                (gs_id, end, start, limit),
            )
            rows = cur.fetchall()

    return {"count": len(rows), "items": rows}


# ----------------------------
# Schedule / Optimization APIs
# ----------------------------

def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _clip_row_to_window(row: dict, qstart: datetime, qend: datetime) -> PassItem | None:
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


@app.get("/schedule/best")
@limiter.limit("30/minute")
def schedule_best(
    request: Request,
    gs_id: int = Query(..., ge=1),
    start: datetime = Query(...),
    end: datetime = Query(...),
    metric: str = Query("duration", pattern="^(duration|max_elev)$"),
    satellite_id: int | None = Query(None, ge=1),
):
    qstart = _to_utc(start)
    qend = _to_utc(end)

    if qstart >= qend:
        raise HTTPException(status_code=400, detail="Invalid time window: 'start' must be < 'end'.")

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
            rows = cur.fetchall()

    items: list[PassItem] = []
    for r in rows:
        p = _clip_row_to_window(r, qstart, qend)
        if p:
            items.append(p)

    chosen, score = best_non_overlapping_weighted(items, metric=metric)  # type: ignore[arg-type]

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


@app.get("/schedule/top")
@limiter.limit("30/minute")
def schedule_top(
    request: Request,
    gs_id: int = Query(..., ge=1),
    start: datetime = Query(...),
    end: datetime = Query(...),
    metric: str = Query("duration", pattern="^(duration|max_elev)$"),
    k: int = Query(5, ge=1, le=100),
    satellite_id: int | None = Query(None, ge=1),
):
    qstart = _to_utc(start)
    qend = _to_utc(end)

    if qstart >= qend:
        raise HTTPException(status_code=400, detail="Invalid time window: 'start' must be < 'end'.")

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
            rows = cur.fetchall()

    items: list[PassItem] = []
    for r in rows:
        p = _clip_row_to_window(r, qstart, qend)
        if p:
            items.append(p)

    topk = top_k_passes(items, metric=metric, k=k)  # type: ignore[arg-type]

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
