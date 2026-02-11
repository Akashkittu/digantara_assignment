# Digantara — Ground Pass Prediction (Backend)

Backend service that:
- Fetches **real-time TLEs** from **CelesTrak**
- Propagates satellite orbits using **SGP4**
- Predicts **visible ground passes** (start/end + duration + max elevation)
- Persists pass windows in **PostgreSQL** for fast overlap queries
- Exposes scheduling APIs: **best non-overlapping schedule** + **top‑K passes**
- Includes **rate limiting**, clean DB error handling, and a lightweight **demo UI** (`/ui`)

> This repo is structured for the Digantara backend assignment: **50 ground stations**, predict for **next 7 days**, enforce **minimum pass duration = 5s**, and support **sub-second queries** via indexing + precomputation.

---

## Contents
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Data Pipeline](#data-pipeline)
- [API](#api)
- [Sample Outputs](#sample-outputs)
- [Database Schema](#database-schema)
- [Design Notes](#design-notes)
- [Troubleshooting](#troubleshooting)

---

## Tech Stack
- **FastAPI** + **Uvicorn**
- **PostgreSQL 16** (Docker)
- **psycopg** (DB driver)
- **Alembic** (migrations)
- **slowapi** (rate limiting)
- **SGP4** (propagation)

---

## Quick Start

### 0) Prereqs
- Python **3.12** (Windows recommended commands use `py -3.12`)
- Docker Desktop (for Postgres)

### 1) Start Postgres
```powershell
docker compose up -d
docker ps
```

### 2) Configure env
Copy:
```powershell
copy .env.example .env
```

`.env`:
```env
DATABASE_URL=postgresql://dg:dgpass@localhost:5432/dg_passes
```

### 3) Install dependencies
```powershell
py -3.12 -m pip install -r requirements.txt
```

### 4) Create tables (migrations)
```powershell
py -3.12 -m alembic upgrade head
```

### 5) Seed 50 ground stations
```powershell
py -3.12 -m app.scripts.seed_ground_stations
```

### 6) Run the API
```powershell
py -3.12 -m uvicorn app.main:app --reload
```

Open:
- Swagger docs: `http://127.0.0.1:8000/docs`
- Demo UI: `http://127.0.0.1:8000/ui`
- Health: `http://127.0.0.1:8000/health`

---

## Data Pipeline

### A) Fetch latest TLEs (CelesTrak)
Fetch from the “active” group (default), store satellites + TLEs:
```powershell
py -3.12 -m app.scripts.fetch_tles --group active --limit 200
```

Notes:
- `--group` maps to CelesTrak group names (e.g., `active`, `stations`, etc.)
- `--limit` limits number of TLE triplets ingested

### B) Generate passes (store in DB)
Generate pass windows for the next N days by scanning in time chunks.

**Fast demo run (recommended first):**
```powershell
py -3.12 -m app.scripts.generate_passes_7d_batched --days 2 --gs-limit 50 --sat-limit 30 --chunk-hours 24 --step 60 --delete-existing
```

**Full run (assignment-style):**
```powershell
py -3.12 -m app.scripts.generate_passes_7d_batched --days 7 --gs-limit 50 --sat-limit 200 --chunk-hours 24 --step 60 --delete-existing
```

Key flags:
- `--days` number of days to generate (max 7 recommended)
- `--gs-limit` number of ground stations (expected **50**)
- `--sat-limit` number of satellites to process
- `--chunk-hours` batch size for time window processing
- `--step` coarse scan step seconds (tradeoff accuracy vs speed)
- `--delete-existing` clears existing passes first (avoids duplicates)

---

## Verify data in Postgres (after Data Pipeline)

### A) Step 1 — open `psql` inside the running Postgres container:


```powershell
docker exec -it digantara_pg psql -U dg -d dg_passes
```

### B) Step 2 — Inside psql, run:
**lists all tables in the current database**
```powershell
\dt
```

**Check data was generated:**
```powershell
select count(*) from satellites;
select count(*) from tles;
select count(*) from passes;
```

---

## API

All endpoints are **GET** and are rate-limited.

### `GET /health`
Sanity check.
```bash
curl http://127.0.0.1:8000/health
```

### `GET /db/health`
Verifies DB connectivity.
```bash
curl http://127.0.0.1:8000/db/health
```

### `GET /ground-stations`
List ground stations.
Query params:
- `limit` (default 200, max 500)

Example:
```bash
curl "http://127.0.0.1:8000/ground-stations?limit=50"
```

### `GET /passes`
Overlap query: returns all passes that overlap a query window.

Query params:
- `gs_id` (required) ground station DB id
- `start` (required) ISO datetime
- `end` (required) ISO datetime
- `limit` (default 200, max 1000)

Overlap logic:
- A pass overlaps the window if: `pass.start < window.end AND pass.end > window.start`

Example:
```bash
curl "http://127.0.0.1:8000/passes?gs_id=1&start=2026-02-08T00:00:00Z&end=2026-02-09T00:00:00Z&limit=50"
```

### `GET /schedule/best`
Computes the **best non-overlapping schedule** for a ground station over a window using **Weighted Interval Scheduling**.

Query params:
- `gs_id`, `start`, `end` (required)
- `metric` (`duration` or `max_elev`, default `duration`)
- `satellite_id` (optional filter)

Example:
```bash
curl "http://127.0.0.1:8000/schedule/best?gs_id=1&start=2026-02-08T00:00:00Z&end=2026-02-09T00:00:00Z&metric=duration"
```

### `GET /schedule/top`
Returns the **top‑K** passes in the window (by metric).

Query params:
- `gs_id`, `start`, `end` (required)
- `metric` (`duration` or `max_elev`, default `duration`)
- `k` (default 5, max 100)
- `satellite_id` (optional filter)

Example:
```bash
curl "http://127.0.0.1:8000/schedule/top?gs_id=1&start=2026-02-08T00:00:00Z&end=2026-02-09T00:00:00Z&metric=duration&k=3"
```

### `GET /ui`
Lightweight HTML UI to test:
- `/passes`
- `/schedule/best`
- `/schedule/top`

Open:
`http://127.0.0.1:8000/ui`

---

## Sample Outputs

### Option 1: Generate **real** outputs automatically (recommended)
Create a script: `app/scripts/generate_sample_outputs.py` (provided separately in this project work) and run:

```powershell
py -3.12 -u app\scripts\generate_sample_outputs.py --gs-id 1 --hours 24 --metric duration --k 3 --out SAMPLE_OUTPUTS.md
```

This writes `SAMPLE_OUTPUTS.md` with **real JSON responses** from your running server.

### Option 2: Manual
- Open `/docs` → try `/passes`, `/schedule/best`, `/schedule/top`
- Copy JSON and paste into README under “Sample Outputs”

### UI Screenshot
1) Open `http://127.0.0.1:8000/ui`    
2) Add:
```md
![Demo UI](docs/ui.png)
```

---

## Database Schema

Core tables (via Alembic migrations):

- `ground_stations(id, code, name, lat, lon, alt_m)`
- `satellites(id, norad_id, name, created_at)`
- `tles(id, satellite_id, line1, line2, epoch, fetched_at)`
- `passes(id, satellite_id, ground_station_id, start_ts, end_ts, duration_s, max_elev_deg)`

Performance indexes:
- `passes(ground_station_id, start_ts)`
- `passes(ground_station_id, end_ts)`
- `passes(satellite_id, start_ts)`
- `tles(satellite_id, fetched_at)`

---

## Design Notes

### Why precompute passes?
For *50 ground stations × many satellites × 7 days*, pass prediction can be huge. Precomputing into Postgres gives:
- Fast overlap queries (index-backed)
- Fast scheduling (window queries + O(n log n) DP)

### Pass prediction approach
- Use SGP4 for satellite state over time
- Convert to local topocentric frame and compute **elevation**
- Detect visibility windows (elevation > 0°)
- Refine rise/set times using bisection
- Enforce **minimum pass duration >= 5 seconds**

### Scheduling
- `best` uses **Weighted Interval Scheduling** (O(n log n))
- `top` returns top‑K passes by metric (duration or max elevation)

### Time handling
- All times are treated as **UTC** internally (`timezone-aware` timestamps)

---

## Troubleshooting

### `/passes` returns empty
Most common reason: passes weren’t generated yet.
1) Fetch TLEs:
```powershell
py -3.12 -m app.scripts.fetch_tles --group active --limit 200
```
2) Generate passes:
```powershell
py -3.12 -m app.scripts.generate_passes_7d_batched --days 2 --gs-limit 50 --sat-limit 30 --chunk-hours 24 --step 60 --delete-existing
```
3) Re-query `/passes`.

### Docker/Postgres not running
- Check `docker ps`
- Restart Docker Desktop
- Re-run `docker compose up -d`

### Alembic errors
- Ensure `.env` exists and `DATABASE_URL` is correct
- Verify Postgres port is `5432` and container is healthy

---

## License
Internal assignment code (use as per assignment instructions).
