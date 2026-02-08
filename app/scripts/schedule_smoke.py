from __future__ import annotations

from datetime import datetime, timezone

from psycopg.rows import dict_row

from app.db.conn import get_conn
from app.schedule.optimizer import PassItem, best_non_overlapping_weighted, top_k_passes


def parse_utc(s: str) -> datetime:
    # accepts "2026-02-08T06:00:00" (no tz) or "...+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def clip_pass(row, qstart: datetime, qend: datetime) -> PassItem | None:
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


def main():
    gs_id = 1
    start = parse_utc("2026-02-08T06:00:00+00:00")
    end = parse_utc("2026-02-09T06:00:00+00:00")

    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, satellite_id, ground_station_id, start_ts, end_ts, duration_s, max_elev_deg
                FROM passes
                WHERE ground_station_id = %s
                  AND start_ts < %s
                  AND end_ts > %s
                ORDER BY end_ts ASC
                """,
                (gs_id, end, start),
            )
            rows = cur.fetchall()

    items = []
    for r in rows:
        p = clip_pass(r, start, end)
        if p:
            items.append(p)

    print(f"[db] candidates={len(items)}")

    best_dur, score_dur = best_non_overlapping_weighted(items, metric="duration")
    print(f"[best duration] count={len(best_dur)} total_duration_s={int(score_dur)}")
    for p in best_dur[:5]:
        print("  ", p.start_ts.isoformat(), "->", p.end_ts.isoformat(), "dur", p.duration_s)

    best_elev, score_elev = best_non_overlapping_weighted(items, metric="max_elev")
    print(f"[best max_elev sum] count={len(best_elev)} score={score_elev:.2f}")
    for p in best_elev[:5]:
        print("  ", p.start_ts.isoformat(), "->", p.end_ts.isoformat(), "max_elev", round(p.max_elev_deg, 2))

    top = top_k_passes(items, metric="duration", k=5)
    print("[top 5 duration]")
    for p in top:
        print("  ", p.duration_s, "s", p.start_ts.isoformat(), "->", p.end_ts.isoformat())

    top2 = top_k_passes(items, metric="max_elev", k=5)
    print("[top 5 max_elev]")
    for p in top2:
        print("  ", round(p.max_elev_deg, 2), "deg", p.start_ts.isoformat(), "->", p.end_ts.isoformat())


if __name__ == "__main__":
    main()
