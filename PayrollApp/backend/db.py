# db.py
import os
from contextlib import contextmanager
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import sql
from dotenv import load_dotenv

load_dotenv()  # reads backend/.env if present

def get_conn():
    url = os.environ.get("DATABASE_URL")
    if not url:
        # Build from parts if DATABASE_URL not set
        host = os.environ.get("DB_HOST", "127.0.0.1")
        port = os.environ.get("DB_PORT", "5432")
        name = os.environ.get("DB_NAME", "wageflow")
        user = os.environ.get("DB_USER", "postgres")
        pwd  = os.environ.get("DB_PASS", "")
        opts = os.environ.get("DB_OPTS", "sslmode=require")
        url = f"postgresql://{user}:{pwd}@{host}:{port}/{name}"
        if opts and "sslmode" in opts and "sslmode=" not in url:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}{opts}"

    return psycopg2.connect(url)




def _append_sslmode_if_local(db_url: str) -> str:
    """
    If host is localhost/127.0.0.1 and no sslmode provided, add sslmode=disable.
    This avoids 'SSL off' vs 'require' confusion on local dev.
    """
    if not db_url:
        return db_url

    parsed = urlparse(db_url)
    host = parsed.hostname or ""
    query = dict(parse_qsl(parsed.query))

    if host in ("localhost", "127.0.0.1") and "sslmode" not in query:
        query["sslmode"] = "disable"
        new_query = urlencode(query)
        parsed = parsed._replace(query=new_query)
        return urlunparse(parsed)

    return db_url

def get_database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL is not set. Add it to .env")
    return _append_sslmode_if_local(url)

@contextmanager
def get_conn():
    """
    Usage:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("select 1;")
                print(cur.fetchone())
    """
    dsn = get_database_url()
    conn = psycopg2.connect(dsn, cursor_factory=RealDictCursor)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def fetch_one(query: str, params=None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            return cur.fetchone()

def fetch_all(query: str, params=None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            return cur.fetchall()

def execute(query: str, params=None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params or ())

def executemany(query: str, seq_of_params):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.executemany(query, seq_of_params)

def ensure_schema():
    """
    Creates minimal tables if they don't exist yet.
    Safe to run multiple times.
    """
    ddl = """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'employee',
        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );

    CREATE TABLE IF NOT EXISTS employees (
        id SERIAL PRIMARY KEY,
        user_id INTEGER UNIQUE REFERENCES users(id) ON DELETE CASCADE,
        full_name TEXT NOT NULL,
        rate NUMERIC(10,2) NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS timesheets (
        id SERIAL PRIMARY KEY,
        employee_id INTEGER REFERENCES employees(id) ON DELETE CASCADE,
        week_start DATE NOT NULL,
        hours NUMERIC(5,2) NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'pending'
    );
    """
    execute(ddl)

if __name__ == "__main__":
    # quick connectivity + schema check you can run: python db.py
    try:
        print("Checking connection…")
        one = fetch_one("select current_user as user, current_database() as db;")
        print(f"Connected as {one['user']} to {one['db']}")
        ensure_schema()
        print("Schema OK (users, employees, timesheets).")
    except Exception as e:
        print("DB check failed:", repr(e))
        raise
