# Digantara — Ground Pass Prediction (Backend)

Backend service that:
- Stores satellites + TLEs (CelesTrak)
- Predicts ground passes using SGP4 + visibility (elevation)
- Persists pass windows in Postgres for fast queries
- Supports overlap queries + scheduling/optimization APIs (best non-overlapping schedule, top-K)
- Has rate limiting + clean DB error handling
- Includes a lightweight demo UI at `/ui` + Swagger at `/docs`

---

## Tech Stack
- FastAPI + Uvicorn
- PostgreSQL 16 (Docker)
- psycopg (DB driver)
- Alembic migrations
- slowapi rate limiting
- SGP4 propagation

---

## Quick Start (Windows PowerShell) — No venv
### 1) Start Postgres
```powershell
docker compose up -d
2) Create .env
Copy the example:

copy .env.example .env
.env.example:

DATABASE_URL=postgresql://dg:dgpass@localhost:5432/dg_passes
3) Install deps (no venv)
py -3.12 -m pip install --user -r requirements.txt
4) Run migrations
py -3.12 -m alembic upgrade head
5) Seed ground stations
Recommended (module mode):

py -3.12 -m app.scripts.seed_ground_stations
6) Run API
py -3.12 -m uvicorn app.main:app --reload
Open:

Swagger UI: http://127.0.0.1:8000/docs

Demo UI: http://127.0.0.1:8000/ui

Health: http://127.0.0.1:8000/health

Database (Docker)
Container name is digantara_pg.

Useful checks:

docker exec -it digantara_pg psql -U dg -d dg_passes -c "select count(*) from ground_stations;"
docker exec -it digantara_pg psql -U dg -d dg_passes -c "select count(*) from satellites;"
docker exec -it digantara_pg psql -U dg -d dg_passes -c "select count(*) from tles;"
docker exec -it digantara_pg psql -U dg -d dg_passes -c "select count(*) from passes;"
Endpoints
Health
GET /health

GET /db/health

Ground stations
GET /ground-stations?limit=200

Pass retrieval (overlap window query)
Returns passes that overlap the query window:

overlaps if: pass.start_ts < end AND pass.end_ts > start

GET /passes?gs_id=1&start=...&end=...&limit=200

Example (PowerShell):

curl.exe "http://127.0.0.1:8000/passes?gs_id=1&start=2026-02-08T06:00:00%2B00:00&end=2026-02-09T06:00:00%2B00:00&limit=200"
Scheduling / Optimization (must-have)
1) Best non-overlapping schedule (optimize objective)
Selects a non-overlapping set of passes that maximizes the chosen metric:

metric=duration → max total duration

metric=max_elev → max total max-elevation sum

GET /schedule/best?gs_id=...&start=...&end=...&metric=duration|max_elev

Example:

curl.exe "http://127.0.0.1:8000/schedule/best?gs_id=1&start=2026-02-08T06:00:00%2B00:00&end=2026-02-09T06:00:00%2B00:00&metric=duration"
2) Top-K passes (simple ranking)
Returns best individual passes by metric (no non-overlap constraint):
GET /schedule/top?gs_id=...&start=...&end=...&metric=duration|max_elev&k=5

Example:

curl.exe "http://127.0.0.1:8000/schedule/top?gs_id=1&start=2026-02-08T06:00:00%2B00:00&end=2026-02-09T06:00:00%2B00:00&metric=max_elev&k=5"
Demo UI (/ui)
Open: http://127.0.0.1:8000/ui

Features:

datetime picker (no need to type ISO)

quick buttons: Now → +6h, +24h, +7d

enforces max 7-day window in the UI (assignment rule)

buttons to call: /passes, /schedule/best, /schedule/top

link to Swagger /docs

Note: UI sends datetime-local values (no timezone). Backend treats them as UTC.

Rate Limiting + Error Handling
Rate limiting
slowapi in-memory limiter (keyed by client IP).

Designed for the assignment; in production, replace with Redis-backed limiter.

DB error handling
Global psycopg.Error handler maps DB errors to clean JSON without leaking SQL internals:

DB unavailable → 503

Bad params/data → 400

Constraint conflicts → 409

Query issues → 500

Pass Generation (batch scripts)
This project supports generating passes and storing them in passes so queries stay fast.

Example (1 sat × 50 GS × 7 days, chunked):

py -3.12 -m app.scripts.generate_passes_7d_batched --days 7 --gs-limit 50 --sat-limit 1 --chunk-hours 24 --step 60 --delete-existing
Example (smaller bulk test):

py -3.12 -m app.scripts.generate_passes_bulk --hours 6 --gs-limit 5 --step 30 --delete-existing
