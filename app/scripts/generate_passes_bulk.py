from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone

from psycopg.rows import dict_row

from app.db.conn import get_conn
from app.orbit.visibility import GroundStation
from app.orbit.pass_prediction import predict_passes


def pick_latest_tle(cur, satellite_id: int | None):
    if satellite_id is None:
        cur.execute(
            """
            SELECT s.id AS satellite_id, s.norad_id, s.name, t.line1, t.line2
            FROM tles t
            JOIN satellites s ON s.id = t.satellite_id
            ORDER BY t.fetched_at DESC
            LIMIT 1
            """
        )
    else:
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
        raise RuntimeError("No TLE found. Run fetch_tles first.")
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--satellite-id", type=int, default=None, help="DB satellite_id (default: latest TLE satellite)")
    ap.add_argument("--hours", type=int, default=6, help="How many hours ahead to generate (default 6)")
    ap.add_argument("--step", type=int, default=30, help="Coarse step seconds for scanning (default 30)")
    ap.add_argument("--gs-limit", type=int, default=5, help="How many ground stations (default 5 for safe test)")
    ap.add_argument("--delete-existing", action="store_true", help="Delete overlapping existing passes in window before inserting")
    args = ap.parse_args()

    start = datetime.now(timezone.utc)
    end = start + timedelta(hours=args.hours)

    # Load satellite + latest TLE + ground stations
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            sat = pick_latest_tle(cur, args.satellite_id)

            cur.execute(
                """
                SELECT id, name, lat, lon, COALESCE(alt_m, 0) AS alt_m
                FROM ground_stations
                ORDER BY code
                LIMIT %s
                """,
                (args.gs_limit,),
            )
            stations = cur.fetchall()

    print(f"[sat] {sat['satellite_id']} | {sat['norad_id']} | {sat['name']}")
    print(f"[win] {start.isoformat()} -> {end.isoformat()} | step={args.step}s")
    print(f"[gs ] count={len(stations)}")

    total_pred = 0
    total_inserted = 0

    with get_conn() as conn:
        with conn.cursor() as cur:
            if args.delete_existing:
                cur.execute(
                    """
                    DELETE FROM passes
                    WHERE satellite_id = %s
                      AND start_ts < %s
                      AND end_ts > %s
                    """,
                    (sat["satellite_id"], end, start),
                )
                print(f"[db] deleted_existing={cur.rowcount}")

            for idx, gs_row in enumerate(stations, start=1):
                gs = GroundStation(
                    lat_deg=float(gs_row["lat"]),
                    lon_deg=float(gs_row["lon"]),
                    alt_m=float(gs_row["alt_m"]),
                )

                passes = predict_passes(
                    line1=sat["line1"],
                    line2=sat["line2"],
                    gs=gs,
                    start=start,
                    end=end,
                    step_seconds=args.step,
                    cutoff_deg=0.0,
                    min_duration_s=5,
                )

                total_pred += len(passes)

                # bulk insert for this GS
                rows = [
                    (
                        sat["satellite_id"],
                        gs_row["id"],
                        p.start_ts,
                        p.end_ts,
                        p.duration_s,
                        p.max_elev_deg,
                    )
                    for p in passes
                ]

                if rows:
                    cur.executemany(
                        """
                        INSERT INTO passes (satellite_id, ground_station_id, start_ts, end_ts, duration_s, max_elev_deg)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (satellite_id, ground_station_id, start_ts, end_ts) DO NOTHING
                        """,
                        rows,
                    )
                    # executemany doesn't give exact rowcount reliably in psycopg,
                    # so we just re-count per station by selecting after if needed later.
                # approximate progress
                if idx % 1 == 0:
                    print(f"[prog] {idx}/{len(stations)} gs done | passes_pred={len(passes)}")

    print(f"[done] total_predicted={total_pred} (inserted ~= {total_pred})")


if __name__ == "__main__":
    main()
