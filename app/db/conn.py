import psycopg
from contextlib import contextmanager
from app.core.config import DATABASE_URL


@contextmanager
def get_conn():
    conn = psycopg.connect(DATABASE_URL, connect_timeout=3)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def check_db() -> None:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
            cur.fetchone()
