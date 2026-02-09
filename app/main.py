from dotenv import load_dotenv

# ✅ Load .env BEFORE importing anything that reads env vars
load_dotenv()

import logging
from datetime import datetime, timezone, timedelta

import psycopg
from psycopg import OperationalError, IntegrityError, DataError, ProgrammingError, InterfaceError
from psycopg.rows import dict_row

from fastapi import FastAPI, Request, Query, status, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse

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


# ----------------------------
# Time window helpers (backend enforcement)
# ----------------------------

def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


MAX_QUERY_WINDOW = timedelta(days=7)


def _validate_window(qstart: datetime, qend: datetime) -> None:
    if qstart >= qend:
        raise HTTPException(status_code=400, detail="Invalid time window: 'start' must be < 'end'.")
    if (qend - qstart) > MAX_QUERY_WINDOW:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid time window: maximum allowed range is {MAX_QUERY_WINDOW.days} days.",
        )


# ✅ For timestamptz columns, use tstzrange (NOT tsrange)
# This matches your GiST index: GIST(ground_station_id, tstzrange(start_ts, end_ts, '[)'))
_OVERLAP_SQL = "tstzrange(start_ts, end_ts, '[)') && tstzrange(%s, %s, '[)')"


@app.get("/passes")
@limiter.limit("60/minute")
def get_passes(
    request: Request,
    gs_id: int = Query(..., ge=1),
    start: datetime = Query(...),
    end: datetime = Query(...),
    limit: int = Query(200, ge=1, le=1000),
):
    # ✅ Backend enforcement: convert to UTC + validate <= 7 days
    qstart = _to_utc(start)
    qend = _to_utc(end)
    _validate_window(qstart, qend)

    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # ✅ Range overlap (uses GiST range index at scale)
            cur.execute(
                f"""
                SELECT id, satellite_id, ground_station_id, start_ts, end_ts, duration_s, max_elev_deg
                FROM passes
                WHERE ground_station_id = %s
                  AND {_OVERLAP_SQL}
                ORDER BY start_ts
                LIMIT %s
                """,
                (gs_id, qstart, qend, limit),
            )
            rows = cur.fetchall()

    return {"count": len(rows), "items": rows}


# ----------------------------
# Schedule / Optimization APIs
# ----------------------------

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
    _validate_window(qstart, qend)

    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            if satellite_id is None:
                cur.execute(
                    f"""
                    SELECT id, satellite_id, ground_station_id, start_ts, end_ts, duration_s, max_elev_deg
                    FROM passes
                    WHERE ground_station_id = %s
                      AND {_OVERLAP_SQL}
                    ORDER BY end_ts ASC
                    """,
                    (gs_id, qstart, qend),
                )
            else:
                cur.execute(
                    f"""
                    SELECT id, satellite_id, ground_station_id, start_ts, end_ts, duration_s, max_elev_deg
                    FROM passes
                    WHERE ground_station_id = %s
                      AND satellite_id = %s
                      AND {_OVERLAP_SQL}
                    ORDER BY end_ts ASC
                    """,
                    (gs_id, satellite_id, qstart, qend),
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
    _validate_window(qstart, qend)

    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            if satellite_id is None:
                cur.execute(
                    f"""
                    SELECT id, satellite_id, ground_station_id, start_ts, end_ts, duration_s, max_elev_deg
                    FROM passes
                    WHERE ground_station_id = %s
                      AND {_OVERLAP_SQL}
                    ORDER BY end_ts ASC
                    """,
                    (gs_id, qstart, qend),
                )
            else:
                cur.execute(
                    f"""
                    SELECT id, satellite_id, ground_station_id, start_ts, end_ts, duration_s, max_elev_deg
                    FROM passes
                    WHERE ground_station_id = %s
                      AND satellite_id = %s
                      AND {_OVERLAP_SQL}
                    ORDER BY end_ts ASC
                    """,
                    (gs_id, satellite_id, qstart, qend),
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


@app.get("/ui", response_class=HTMLResponse)
@limiter.limit("60/minute")
def ui(request: Request):
    return HTMLResponse(
        """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Ground Pass Demo UI</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; max-width: 1100px; }
    .row { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; align-items: end; }
    label { font-size: 12px; color: #333; display: block; margin-bottom: 4px; }
    input, select { padding: 8px; width: 260px; }
    input[type="datetime-local"]{ width: 320px; }
    button { padding: 10px 14px; cursor: pointer; }
    .smallbtn { padding: 8px 10px; font-size: 12px; }
    pre { background:#111; color:#0f0; padding:12px; overflow:auto; border-radius: 8px; }
    .hint { color:#666; font-size: 12px; margin-top: 8px; }
    .card { border: 1px solid #ddd; border-radius: 10px; padding: 12px; }
  </style>
</head>
<body>
  <h2>Digantara Ground Pass Demo</h2>

  <div class="card">
    <div class="row">
      <div>
        <label>Ground station id (gs_id)</label>
        <input id="gs_id" type="number" value="1" min="1" />
      </div>

      <div>
        <label>Start (UTC)</label>
        <input id="start" type="datetime-local" step="1" />
      </div>

      <div>
        <label>End (UTC) — max 7 days</label>
        <input id="end" type="datetime-local" step="1" />
      </div>
    </div>

    <div class="row">
      <div>
        <label>Metric</label>
        <select id="metric">
          <option value="duration">duration</option>
          <option value="max_elev">max_elev</option>
        </select>
      </div>

      <div>
        <label>Top K</label>
        <input id="k" type="number" value="5" min="1" max="100" />
      </div>

      <div>
        <label>Optional satellite_id</label>
        <input id="satellite_id" type="number" placeholder="(blank = all)" min="1" />
      </div>
    </div>

    <div class="row">
      <button class="smallbtn" onclick="setNowUtc()">Now UTC</button>
      <button class="smallbtn" onclick="setRangeHours(6)">Now → +6h</button>
      <button class="smallbtn" onclick="setRangeHours(24)">Now → +24h</button>
      <button class="smallbtn" onclick="setRangeDays(7)">Now → +7d</button>
    </div>

    <div class="row">
      <button onclick="callApi('passes')">Get Passes</button>
      <button onclick="callApi('best')">Best Schedule</button>
      <button onclick="callApi('top')">Top K</button>
      <button onclick="window.open('/docs','_blank')">Open Swagger (/docs)</button>
    </div>
  </div>

  <pre id="out">{ "ready": true }</pre>

  <div class="hint">
    Times are treated as <b>UTC</b>. Max allowed window is <b>7 days</b> (assignment rule).
  </div>

<script>
  function qs(id){ return document.getElementById(id).value.trim(); }
  function pad2(n){ return String(n).padStart(2,'0'); }

  // Convert Date -> "YYYY-MM-DDTHH:MM:SS" in UTC for datetime-local input
  function toDatetimeLocalUTC(d){
    return `${d.getUTCFullYear()}-${pad2(d.getUTCMonth()+1)}-${pad2(d.getUTCDate())}T${pad2(d.getUTCHours())}:${pad2(d.getUTCMinutes())}:${pad2(d.getUTCSeconds())}`;
  }

  // Parse "YYYY-MM-DDTHH:MM:SS" as UTC Date object
  function parseUtcFromDatetimeLocal(s){
    const [datePart, timePart] = s.split("T");
    const [Y,M,D] = datePart.split("-").map(Number);
    const [h,m,sec] = timePart.split(":").map(Number);
    return new Date(Date.UTC(Y, M-1, D, h, m, sec || 0));
  }

  function setNowUtc(){
    const now = new Date();
    document.getElementById('start').value = toDatetimeLocalUTC(now);
    const plus24 = new Date(now.getTime() + 24*3600*1000);
    document.getElementById('end').value = toDatetimeLocalUTC(plus24);
  }

  function setRangeHours(h){
    const now = new Date();
    const end = new Date(now.getTime() + h*3600*1000);
    document.getElementById('start').value = toDatetimeLocalUTC(now);
    document.getElementById('end').value = toDatetimeLocalUTC(end);
  }

  function setRangeDays(d){
    if(d > 7) d = 7; // hard cap
    const now = new Date();
    const end = new Date(now.getTime() + d*24*3600*1000);
    document.getElementById('start').value = toDatetimeLocalUTC(now);
    document.getElementById('end').value = toDatetimeLocalUTC(end);
  }

  // Default: now -> +24h
  setRangeDays(1);

  async function callApi(kind){
    const gs_id = qs('gs_id');
    const start = qs('start'); // "YYYY-MM-DDTHH:MM:SS"
    const end = qs('end');
    const metric = qs('metric');
    const k = qs('k');
    const satellite_id = qs('satellite_id');

    const out = document.getElementById('out');

    if(!start || !end){
      out.textContent = "Error: start and end are required.";
      return;
    }

    // ✅ Enforce max 7 days window in UI
    const ds = parseUtcFromDatetimeLocal(start);
    const de = parseUtcFromDatetimeLocal(end);
    const diffMs = de - ds;

    if(diffMs <= 0){
      out.textContent = "Error: end must be after start.";
      return;
    }

    const maxMs = 7 * 24 * 3600 * 1000;
    if(diffMs > maxMs){
      out.textContent = "Error: Maximum allowed window is 7 days (assignment rule).";
      return;
    }

    let url = '';
    const enc = encodeURIComponent;

    if(kind === 'passes'){
      url = `/passes?gs_id=${enc(gs_id)}&start=${enc(start)}&end=${enc(end)}&limit=200`;
    } else if(kind === 'best'){
      url = `/schedule/best?gs_id=${enc(gs_id)}&start=${enc(start)}&end=${enc(end)}&metric=${enc(metric)}`;
      if(satellite_id) url += `&satellite_id=${enc(satellite_id)}`;
    } else if(kind === 'top'){
      url = `/schedule/top?gs_id=${enc(gs_id)}&start=${enc(start)}&end=${enc(end)}&metric=${enc(metric)}&k=${enc(k)}`;
      if(satellite_id) url += `&satellite_id=${enc(satellite_id)}`;
    }

    out.textContent = "Loading...";

    try{
      const res = await fetch(url);
      const data = await res.json();
      out.textContent = JSON.stringify({ url, status: res.status, data }, null, 2);
    } catch(e){
      out.textContent = "Error: " + e.toString();
    }
  }
</script>
</body>
</html>
""".strip()
    )
