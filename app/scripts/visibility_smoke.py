from datetime import datetime, timedelta, timezone

from app.db.conn import get_conn
from app.orbit.sgp4_propagator import propagate_tle
from app.orbit.visibility import GroundStation, elevation_deg


def main():
    with get_conn() as conn:
        with conn.cursor() as cur:
            # 1) latest TLE
            cur.execute(
                """
                SELECT s.norad_id, s.name, t.line1, t.line2
                FROM tles t
                JOIN satellites s ON s.id = t.satellite_id
                ORDER BY t.fetched_at DESC
                LIMIT 1
                """
            )
            norad_id, name, line1, line2 = cur.fetchone()

            # 2) first ground station
            cur.execute(
                "SELECT name, lat AS lat_deg, lon AS lon_deg, COALESCE(alt_m, 0) FROM ground_stations ORDER BY id LIMIT 1"
            )
            gs_name, lat, lon, alt_m = cur.fetchone()

    gs = GroundStation(lat_deg=float(lat), lon_deg=float(lon), alt_m=float(alt_m))
    print(f"[sat] {norad_id} | {name}")
    print(f"[gs ] {gs_name} | lat={lat}, lon={lon}, alt_m={alt_m}")

    start = datetime.now(timezone.utc)
    end = start + timedelta(hours=3)
    step = timedelta(seconds=30)

    times = []
    t = start
    while t <= end:
        times.append(t)
        t += step

    states = propagate_tle(line1, line2, times)

    # print moments when elevation crosses 0
    prev_el = None
    for st in states:
        el = elevation_deg(st.r_km, st.t, gs)
        if prev_el is not None:
            if prev_el <= 0.0 and el > 0.0:
                print("[rise]", st.t.isoformat(), "el=", round(el, 2))
            if prev_el > 0.0 and el <= 0.0:
                print("[set ]", st.t.isoformat(), "el=", round(el, 2))
        prev_el = el

    print("[done]")


if __name__ == "__main__":
    main()
