import argparse
import re
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

from dotenv import load_dotenv
load_dotenv()

from app.db.conn import get_conn


BASE_URL = "https://celestrak.org/NORAD/elements/gp.php"


def build_url(group: str) -> str:
    return f"{BASE_URL}?GROUP={group}&FORMAT=tle"


def fetch_text(url: str, timeout_s: int = 30) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Digantara-GroundPass/0.1", "Accept": "text/plain"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def parse_tle_epoch(line1: str):
    # epoch is YYDDD.DDDDDDDD located at line1[18:32]
    s = line1[18:32].strip()
    if not s:
        return None
    if not re.match(r"^\d{5}(\.\d+)?$", s):
        return None

    yy = int(s[:2])
    year = 2000 + yy if yy < 57 else 1900 + yy
    doy = float(s[2:])

    day = int(doy)
    frac = doy - day
    return datetime(year, 1, 1, tzinfo=timezone.utc) + timedelta(
        days=day - 1, seconds=frac * 86400.0
    )


def parse_tle_blocks(text: str):
    lines = [ln.strip("\r") for ln in text.splitlines() if ln.strip()]
    out = []
    i = 0
    while i + 2 < len(lines):
        name = lines[i].strip()
        l1 = lines[i + 1].strip()
        l2 = lines[i + 2].strip()

        if not (l1.startswith("1 ") and l2.startswith("2 ")):
            i += 1
            continue

        norad_raw = l1[2:7].strip()
        if not norad_raw.isdigit():
            i += 3
            continue

        out.append(
            {
                "name": name,
                "line1": l1,
                "line2": l2,
                "norad_id": int(norad_raw),
                "epoch_utc": parse_tle_epoch(l1),
            }
        )
        i += 3

    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", default="active")
    ap.add_argument("--limit", type=int, default=200)  # safe default
    args = ap.parse_args()

    url = build_url(args.group)
    print(f"[fetch] {url}")

    try:
        text = fetch_text(url)
    except Exception as e:
        print(f"[error] fetch failed: {e}", file=sys.stderr)
        sys.exit(2)

    blocks = parse_tle_blocks(text)
    if not blocks:
        print("[error] parsed 0 TLEs (format changed?)", file=sys.stderr)
        sys.exit(3)

    blocks = blocks[: max(args.limit, 0)]
    print(f"[parse] parsed={len(blocks)}")

    sat_upserts = 0
    tle_inserts = 0
    tle_skips = 0

    with get_conn() as conn:
        with conn.cursor() as cur:
            for b in blocks:
                # upsert satellite
                cur.execute(
                    """
                    INSERT INTO satellites (norad_id, name)
                    VALUES (%s, %s)
                    ON CONFLICT (norad_id) DO UPDATE SET name = EXCLUDED.name
                    RETURNING id
                    """,
                    (b["norad_id"], b["name"]),
                )
                sat_id = cur.fetchone()[0]
                sat_upserts += 1

                # simple de-dupe: if latest stored TLE matches, skip
                cur.execute(
                    """
                    SELECT line1, line2
                    FROM tles
                    WHERE satellite_id = %s
                    ORDER BY fetched_at DESC
                    LIMIT 1
                    """,
                    (sat_id,),
                )
                prev = cur.fetchone()
                if prev and prev[0] == b["line1"] and prev[1] == b["line2"]:
                    tle_skips += 1
                    continue

                # insert new TLE row
                cur.execute(
                    """
                    INSERT INTO tles (satellite_id, line1, line2, epoch)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (sat_id, b["line1"], b["line2"], b["epoch_utc"]),
                )
                tle_inserts += 1

    print(f"[db] satellites_upserted={sat_upserts} tles_inserted={tle_inserts} skipped={tle_skips}")
    print("[done]")


if __name__ == "__main__":
    main()
