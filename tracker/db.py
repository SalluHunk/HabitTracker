"""Database connection adapter — supports SQLite (local) and Postgres (prod via DATABASE_URL)."""
import os
import sqlite3
from contextlib import contextmanager

DATABASE_URL = os.environ.get("DATABASE_URL", "")
IS_POSTGRES = DATABASE_URL.startswith("postgres")

if IS_POSTGRES:
    import psycopg2
    import psycopg2.extras
    # Render gives "postgres://" — psycopg2 needs "postgresql://"
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


def _adapt_query(q: str) -> str:
    """Translate SQLite '?' placeholders to Postgres '%s'."""
    if not IS_POSTGRES:
        return q
    return q.replace("?", "%s")


@contextmanager
def connect():
    if IS_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        os.makedirs("data", exist_ok=True)
        conn = sqlite3.connect("data/habits.db")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def execute(q: str, params=()):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(_adapt_query(q), params)
        return cur


def query_one(q: str, params=()):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(_adapt_query(q), params)
        row = cur.fetchone()
        return dict(row) if row else None


def query_all(q: str, params=()):
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(_adapt_query(q), params)
        return [dict(r) for r in cur.fetchall()]


def insert_returning_id(q: str, params=()):
    """INSERT and return new row id. Works for both SQLite (lastrowid) and Postgres (RETURNING id)."""
    with connect() as conn:
        cur = conn.cursor()
        if IS_POSTGRES:
            cur.execute(_adapt_query(q) + " RETURNING id", params)
            return cur.fetchone()["id"]
        else:
            cur.execute(q, params)
            return cur.lastrowid


def execute_script(script: str):
    """Run multiple statements separated by semicolons. Used for schema creation only."""
    with connect() as conn:
        cur = conn.cursor()
        if IS_POSTGRES:
            cur.execute(script)
        else:
            cur.executescript(script)
