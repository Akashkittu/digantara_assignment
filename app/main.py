from dotenv import load_dotenv

# ✅ Load .env BEFORE importing anything that reads env vars
load_dotenv()

import logging
import psycopg
from psycopg import OperationalError, IntegrityError, DataError, ProgrammingError, InterfaceError

from fastapi import FastAPI, Request, Query, status
from fastapi.responses import JSONResponse

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from datetime import datetime
from psycopg.rows import dict_row

from app.db.conn import check_db, get_conn


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


# Example query endpoint (works after passes table exists)
@app.get("/passes")
@limiter.limit("60/minute")
def get_passes(
    request: Request,
    gs_id: int = Query(..., ge=1),
    start: datetime = Query(...),
    end: datetime = Query(...),
    limit: int = Query(200, ge=1, le=1000),
):
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT satellite_id, ground_station_id, start_ts, end_ts, duration_s, max_elev_deg
                FROM passes
                WHERE ground_station_id = %s
                  AND start_ts >= %s
                  AND start_ts < %s
                ORDER BY start_ts
                LIMIT %s
                """,
                (gs_id, start, end, limit),
            )
            rows = cur.fetchall()

    return {"count": len(rows), "items": rows}
