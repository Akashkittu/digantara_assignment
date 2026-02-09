# Digantara - Ground Pass Prediction: Explanatory Notes & Architecture


## What this project does 

This backend predicts when a satellite is visible from a ground station (a “pass”).  
It fetches the latest satellite TLE data, propagates orbits using SGP4, detects visibility windows (start/end),
stores those windows in PostgreSQL, and exposes APIs to query passes and build a best non-overlapping tracking schedule.

## High-level architecture

```text
                    (1) Fetch Latest TLEs
                 +------------------------+
                 |  app/scripts/fetch_tles|
                 |  - CelesTrak "active"  |
                 +-----------+------------+
                             |
                             v
     +-------------------------------+     +----------------------------+
     | PostgreSQL (Docker)           |     | Ground Stations Seed        |
     | - satellites                  |<----| app/scripts/seed_ground_...|
     | - tles (latest per satellite) |     | data/ground_stations.csv   |
     +---------------+---------------+     +----------------------------+
                     |
                     | (2) Offline / batch precompute
                     v
            +-------------------------------+
            | Pass Generator (SGP4)         |
            | app/scripts/generate_passes_* |
            |  - coarse scan + bisection    |
            +---------------+---------------+
                            |
                            v
     +-------------------------------+
     | PostgreSQL                    |
     | - passes (start/end/duration) |
     | - GiST overlap index for fast |
     |   window queries              |
     +---------------+---------------+
                     |
                     | (3) Online queries
                     v
     +-------------------------------+
     | FastAPI Server (app/main.py)  |
     |  - /passes  (overlap query)   |
     |  - /schedule/best (DP)        |
     |  - /schedule/top              |
     |  - /network/schedule/best     |
     |  - /ui demo page              |
     +-------------------------------+
```

## Database schema (summary)

- `ground_stations(id, code, name, lat, lon, alt_m)`
- `satellites(id, norad_id, name, created_at)`
- `tles(id, satellite_id, line1, line2, epoch, fetched_at)`
- `passes(id, satellite_id, ground_station_id, start_ts, end_ts, duration_s, max_elev_deg)`

### Fast overlap queries

`/passes` uses overlap predicate:

```sql
WHERE ground_station_id = :gs_id
  AND tstzrange(start_ts, end_ts, '[)') && tstzrange(:start, :end, '[)')
```

A GiST index on `(ground_station_id, tstzrange(start_ts,end_ts))` (via `btree_gist`) makes this fast.

## How to run (copy/paste)

```powershell
docker compose up -d
py -3.12 -m pip install -r requirements.txt
py -3.12 -m alembic upgrade head
py -3.12 -m app.scripts.seed_ground_stations
py -3.12 -m app.scripts.fetch_tles --group active --limit 200
py -3.12 -m app.scripts.generate_passes_7d_batched --days 2 --gs-limit 50 --sat-limit 30 --chunk-hours 24 --step 60 --delete-existing
py -3.12 -m uvicorn app.main:app --reload
```
