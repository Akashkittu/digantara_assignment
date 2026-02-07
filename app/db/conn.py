import psycopg
from app.core.config import DATABASE_URL

def check_db() -> None:
    # simple, fast, reliable connectivity check
    with psycopg.connect(DATABASE_URL, connect_timeout=3) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
            cur.fetchone()
