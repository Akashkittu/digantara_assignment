import csv
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from app.db.conn import get_conn


CSV_PATH_DEFAULT = Path("data/ground_stations.csv")


def seed(csv_path: Path) -> int:
    if not csv_path.exists():
        raise RuntimeError(f"CSV not found: {csv_path}")

    rows = []
    with csv_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required = {"code", "name", "lat", "lon", "alt_m"}
        if set(reader.fieldnames or []) != required:
            raise RuntimeError(f"CSV header must be exactly: {sorted(required)}")

        for r in reader:
            code = r["code"].strip().upper()
            name = r["name"].strip()
            lat = float(r["lat"])
            lon = float(r["lon"])
            alt_m = float(r["alt_m"])

            if not (-90 <= lat <= 90):
                raise RuntimeError(f"Invalid lat for {code}: {lat}")
            if not (-180 <= lon <= 180):
                raise RuntimeError(f"Invalid lon for {code}: {lon}")

            rows.append((code, name, lat, lon, alt_m))

    sql = """
    INSERT INTO ground_stations (code, name, lat, lon, alt_m)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (code) DO UPDATE
      SET name = EXCLUDED.name,
          lat  = EXCLUDED.lat,
          lon  = EXCLUDED.lon,
          alt_m= EXCLUDED.alt_m
    """

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.executemany(sql, rows)

    return len(rows)


if __name__ == "__main__":
    n = seed(CSV_PATH_DEFAULT)
    print(f"Seeded/updated {n} ground stations.")
