from datetime import datetime, timedelta, timezone

from app.db.conn import get_conn
from app.orbit.sgp4_propagator import propagate_tle


def main():
    # pick the most recently fetched TLE in your DB
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT s.norad_id, s.name, t.line1, t.line2
                FROM tles t
                JOIN satellites s ON s.id = t.satellite_id
                ORDER BY t.fetched_at DESC
                LIMIT 1
                """
            )
            row = cur.fetchone()

    if not row:
        raise RuntimeError("No TLEs found. Run fetch_tles first.")

    norad_id, name, line1, line2 = row
    print(f"[tle] {norad_id} | {name}")

    start = datetime.now(timezone.utc)
    end = start + timedelta(days=7)

    # for a quick test, propagate every 10 minutes
    step = timedelta(minutes=10)
    times = []
    t = start
    while t <= end:
        times.append(t)
        t += step

    states = propagate_tle(line1, line2, times)

    print(f"[prop] points={len(states)}")
    print("[first]", states[0].t.isoformat(), "r_km=", states[0].r_km, "v_km_s=", states[0].v_km_s)
    print("[last ]", states[-1].t.isoformat(), "r_km=", states[-1].r_km, "v_km_s=", states[-1].v_km_s)



if __name__ == "__main__":
    main()
