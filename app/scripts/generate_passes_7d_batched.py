from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone

from psycopg.rows import dict_row

from app.db.conn import get_conn
from app.orbit.visibility import GroundStation
from app.orbit.pass_prediction import predict_passes


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def load_ground_stations(gs_limit: int):
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, name, lat, lon, COALESCE(alt_m, 0) AS alt_m
                FROM ground_stations
                ORDER BY code
                LIMIT %s
                """,
                (gs_limit,),
            )
            return cur.fetchall()


def load_latest_tles(sat_limit: int, satellite_id: int | None):
    """
    Returns list of rows:
      {satellite_id, norad_id, name, line1, line2}
    """
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            if satellite_id is not None:
                cur.execute(
                    """
                    SELECT s.id AS satellite_id, s.norad_id, s.name, t.line1, t.line2
                    FROM tles t
                    JOIN satellites s ON s.id = t.satellite_id
                    WHERE s.id = %s
                    ORDER BY t.fetched_at DESC
                    LIMIT 1
                    """,
                    (satellite_id,),
                )
                row = cur.fetchone()
                if not row:
                    raise RuntimeError("No TLE found for given satellite_id.")
                return [row]

            # latest TLE per satellite
            cur.execute(
                """
                SELECT DISTINCT ON (t.satellite_id)
                    s.id AS satellite_id, s.norad_id, s.name, t.line1, t.line2
                FROM tles t
                JOIN satellites s ON s.id = t.satellite_id
                ORDER BY t.satellite_id, t.fetched_at DESC
                LIMIT %s
                """,
                (sat_limit,),
            )
            rows = cur.fetchall()
            if not rows:
                raise RuntimeError("No TLEs found. Run fetch_tles first.")
            return rows


def delete_existing_passes(sat_id: int, start: datetime, end: datetime) -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM passes
                WHERE satellite_id = %s
                  AND start_ts < %s
                  AND end_ts > %s
                """,
                (sat_id, end, start),
            )
            return cur.rowcount


def insert_pass_rows(rows: list[tuple]) -> None:
    if not rows:
        return
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO passes (satellite_id, ground_station_id, start_ts, end_ts, duration_s, max_elev_deg)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (satellite_id, ground_station_id, start_ts, end_ts) DO NOTHING
                """,
                rows,
            )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--gs-limit", type=int, default=50)

    # satellites
    ap.add_argument("--satellite-id", type=int, default=None, help="Use one satellite id (DB id)")
    ap.add_argument("--sat-limit", type=int, default=1, help="How many satellites to process (default 1)")

    # batching/perf
    ap.add_argument("--chunk-hours", type=int, default=24, help="Time chunk size (default 24h)")
    ap.add_argument("--step", type=int, default=60, help="Coarse scan step seconds (default 60)")
    ap.add_argument("--delete-existing", action="store_true")

    args = ap.parse_args()

    start = utcnow()
    end = start + timedelta(days=args.days)

    stations = load_ground_stations(args.gs_limit)
    sats = load_latest_tles(args.sat_limit, args.satellite_id)

    print(f"[win] {start.isoformat()} -> {end.isoformat()} | days={args.days}")
    print(f"[cfg] gs={len(stations)} | sats={len(sats)} | chunk_hours={args.chunk_hours} | step={args.step}s")

    for si, sat in enumerate(sats, start=1):
        sat_id = sat["satellite_id"]
        print(f"\n[sat {si}/{len(sats)}] {sat_id} | {sat['norad_id']} | {sat['name']}")

        if args.delete_existing:
            deleted = delete_existing_passes(sat_id, start, end)
            print(f"[db] deleted_existing={deleted}")

        # per station, chunk the time range
        for gi, gs_row in enumerate(stations, start=1):
            gs = GroundStation(
                lat_deg=float(gs_row["lat"]),
                lon_deg=float(gs_row["lon"]),
                alt_m=float(gs_row["alt_m"]),
            )

            chunk_start = start
            station_pred = 0
            station_rows: list[tuple] = []

            while chunk_start < end:
                chunk_end = min(chunk_start + timedelta(hours=args.chunk_hours), end)

                # expand the chunk slightly so bisection/rise detection is stable at boundaries
                margin = timedelta(minutes=10)
                scan_start = max(start, chunk_start - margin)
                scan_end = min(end, chunk_end + margin)

                predicted = predict_passes(
                    line1=sat["line1"],
                    line2=sat["line2"],
                    gs=gs,
                    start=scan_start,
                    end=scan_end,
                    step_seconds=args.step,
                    cutoff_deg=0.0,
                    min_duration_s=5,
                )

                for p in predicted:
                    # keep each pass only once based on where it STARTS
                    keep = (p.start_ts >= chunk_start and p.start_ts < chunk_end)

                    # special: if we start our whole window during a pass, include it once in the first chunk
                    if chunk_start == start and (p.start_ts < start and p.end_ts > start):
                        keep = True

                    if not keep:
                        continue

                    # clip to [start,end]
                    s = max(p.start_ts, start)
                    e = min(p.end_ts, end)
                    if e <= s:
                        continue

                    dur = int(round((e - s).total_seconds()))
                    if dur < 5:
                        continue

                    station_rows.append(
                        (sat_id, gs_row["id"], s, e, dur, float(p.max_elev_deg))
                    )
                    station_pred += 1

                chunk_start = chunk_end

            insert_pass_rows(station_rows)

            if gi % 5 == 0 or gi == len(stations):
                print(f"[gs {gi}/{len(stations)}] predicted={station_pred}")

    print("\n[done]")


if __name__ == "__main__":
    main()
