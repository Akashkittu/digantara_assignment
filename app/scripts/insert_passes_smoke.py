from datetime import datetime, timedelta, timezone

from psycopg.rows import dict_row

from app.db.conn import get_conn
from app.orbit.visibility import GroundStation
from app.orbit.pass_prediction import predict_passes


def main():
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            # latest TLE + satellite id
            cur.execute(
                """
                SELECT s.id AS satellite_id, s.norad_id, s.name, t.line1, t.line2
                FROM tles t
                JOIN satellites s ON s.id = t.satellite_id
                ORDER BY t.fetched_at DESC
                LIMIT 1
                """
            )
            sat = cur.fetchone()
            if not sat:
                raise RuntimeError("No TLEs found. Run fetch_tles first.")

            # ground station id=1
            cur.execute(
                """
                SELECT id, name, lat, lon, COALESCE(alt_m, 0) AS alt_m
                FROM ground_stations
                WHERE id = 1
                """
            )
            gs_row = cur.fetchone()
            if not gs_row:
                raise RuntimeError("Ground station id=1 not found. Run seed script.")

    gs = GroundStation(
        lat_deg=float(gs_row["lat"]),
        lon_deg=float(gs_row["lon"]),
        alt_m=float(gs_row["alt_m"]),
    )

    start = datetime.now(timezone.utc)
    end = start + timedelta(hours=6)

    passes = predict_passes(
        line1=sat["line1"],
        line2=sat["line2"],
        gs=gs,
        start=start,
        end=end,
        step_seconds=30,
        cutoff_deg=0.0,
        min_duration_s=5,
    )

    print(f"[sat] {sat['norad_id']} | {sat['name']} (satellite_id={sat['satellite_id']})")
    print(f"[gs ] {gs_row['name']} (gs_id={gs_row['id']})")
    print(f"[pred] passes={len(passes)}")

    inserted = 0
    with get_conn() as conn:
        with conn.cursor() as cur:
            for p in passes:
                cur.execute(
                    """
                    INSERT INTO passes (satellite_id, ground_station_id, start_ts, end_ts, duration_s, max_elev_deg)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (satellite_id, ground_station_id, start_ts, end_ts) DO NOTHING
                    """,
                    (
                        sat["satellite_id"],
                        gs_row["id"],
                        p.start_ts,
                        p.end_ts,
                        p.duration_s,
                        p.max_elev_deg,
                    ),
                )
                inserted += cur.rowcount

    print(f"[db] inserted={inserted}")


if __name__ == "__main__":
    main()
