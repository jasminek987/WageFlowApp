# seed_pg.py — aligned with db.py schema; idempotent; FK-safe
import os
from datetime import date, timedelta
from decimal import Decimal
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

import psycopg2
from psycopg2.extras import execute_values
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

load_dotenv()

def _dsn_with_local_sslmode(url: str) -> str:
    if not url:
        raise SystemExit("Set DATABASE_URL (e.g., postgresql://user:pass@127.0.0.1:5432/wageflow)")
    parsed = urlparse(url)
    host = parsed.hostname or ""
    q = dict(parse_qsl(parsed.query))
    if host in ("127.0.0.1", "localhost") and "sslmode" not in q:
        q["sslmode"] = "disable"
        parsed = parsed._replace(query=urlencode(q))
        return parsed.geturl()
    return url

URL = _dsn_with_local_sslmode(os.getenv("DATABASE_URL", "").strip())
conn = psycopg2.connect(URL)
conn.autocommit = False
cur = conn.cursor()

# ------------------------
# Schema ensure / heal
# ------------------------
DDL = """
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

-- Ensure employees.email exists (used by UI/data)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name='employees' AND column_name='email'
  ) THEN
    ALTER TABLE employees ADD COLUMN email TEXT UNIQUE;
  END IF;
END$$;

CREATE TABLE IF NOT EXISTS timesheets (
  id SERIAL PRIMARY KEY,
  employee_id INTEGER REFERENCES employees(id) ON DELETE CASCADE,
  week_start DATE NOT NULL,
  hours NUMERIC(5,2) NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'pending'
);
"""
cur.execute(DDL)

# ------------------------
# Helpers
# ------------------------
def upsert_user(email: str, role: str, password_plain: str) -> int:
    cur.execute("SELECT id FROM users WHERE email=%s LIMIT 1;", (email,))
    row = cur.fetchone()
    pw_hash = generate_password_hash(password_plain)
    if row:
        uid = row[0]
        cur.execute(
            "UPDATE users SET role=%s, password_hash=%s WHERE id=%s;",
            (role, pw_hash, uid),
        )
        return uid
    cur.execute(
        "INSERT INTO users (email, role, password_hash) VALUES (%s,%s,%s) RETURNING id;",
        (email, role, pw_hash),
    )
    return cur.fetchone()[0]

def upsert_employee(full_name: str, email: str, rate: Decimal, user_id: int) -> int:
    cur.execute("SELECT id FROM employees WHERE email=%s LIMIT 1;", (email,))
    row = cur.fetchone()
    if row:
        emp_id = row[0]
        cur.execute(
            "UPDATE employees SET full_name=%s, rate=%s, user_id=COALESCE(user_id,%s) WHERE id=%s;",
            (full_name, rate, user_id, emp_id),
        )
        return emp_id
    cur.execute(
        "INSERT INTO employees (user_id, full_name, email, rate) VALUES (%s,%s,%s,%s) RETURNING id;",
        (user_id, full_name, email, rate),
    )
    return cur.fetchone()[0]

# ------------------------
# Seed data
# ------------------------
# Manager account
manager_uid = upsert_user("manager@company.com", "manager", "admin")

# Employees
EMPLOYEES = [
    ("Abby Gingell",       "abby.gingell@wageflow.com",       Decimal("24.50")),
    ("Alex White",         "alex.white@wageflow.com",         Decimal("23.00")),
    ("George Brown",       "george.brown@wageflow.com",       Decimal("22.75")),
    ("Ashley Harold",      "ashley.harold@wageflow.com",      Decimal("25.00")),
    ("Coby Campbell",      "coby.campbell@wageflow.com",      Decimal("21.50")),
    ("Christina Mavridis", "christina.mavridis@wageflow.com", Decimal("26.00")),
    ("Hanna Larson",       "hanna.larson@wageflow.com",       Decimal("22.00")),
    ("Izzy Rose",          "izzy.rose@wageflow.com",          Decimal("20.75")),
    ("Sydney Stewart",     "sydney.stewart@wageflow.com",     Decimal("23.25")),
    ("Ryan Taylor",        "ryan.taylor@wageflow.com",        Decimal("24.00")),
]

emp_ids = []
for full_name, email, rate in EMPLOYEES:
    uid = upsert_user(email, "employee", "1234")  # each employee can log in with their email / "1234"
    emp_id = upsert_employee(full_name, email, rate, uid)
    emp_ids.append(emp_id)

# Timesheets for 5 recent weeks
start_week = date(2025, 10, 13)  # adjust if you want different weeks
ts_rows = []
for idx, emp_id in enumerate(emp_ids, start=1):
    for i, hours in enumerate([38, 40, 36, 39, 35]):
        week_start = start_week + timedelta(weeks=i)
        status = "approved" if (i + idx) % 3 == 0 else "pending"
        ts_rows.append((emp_id, week_start, Decimal(str(hours)), status))

execute_values(
    cur,
    "INSERT INTO timesheets (employee_id, week_start, hours, status) VALUES %s ON CONFLICT DO NOTHING;",
    ts_rows,
)

# in your seed, after inserting a payslip row with id -> new_id and employee_id -> eid
pdf_dir = Path("storage/payslips") / str(eid)
pdf_dir.mkdir(parents=True, exist_ok=True)
pdf_file = pdf_dir / f"{new_id}.pdf"

# write a tiny unique PDF placeholder (or copy a template). For now, write bytes so it exists:
pdf_file.write_bytes(b"%PDF-1.4\n% unique stub for testing\n%%EOF\n")

# update payslip record with relative path
cur.execute("UPDATE payslips SET pdf_path=%s WHERE id=%s", (str(pdf_file), new_id))


conn.commit()
cur.close()
conn.close()
print("✅ Seed complete: manager + 10 users, employees linked, and timesheets inserted.")
