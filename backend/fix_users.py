import os, psycopg2
from werkzeug.security import generate_password_hash

dsn = os.environ.get("DATABASE_URL") or "postgresql://wageflow:WageflowStrong!123@127.0.0.1:5432/wageflow"
conn = psycopg2.connect(dsn)
cur = conn.cursor()

def upsert_user(email, role, raw_pwd):
    h = generate_password_hash(raw_pwd)
    # update if exists, else insert (schema: email, role, password_hash)
    cur.execute("UPDATE users SET password_hash=%s, role=%s WHERE lower(email)=lower(%s) RETURNING id",
                (h, role, email))
    if cur.rowcount == 0:
        cur.execute("INSERT INTO users (email, role, password_hash) VALUES (%s,%s,%s) RETURNING id",
                    (email, role, h))
    return cur.fetchone()[0]

# Manager
upsert_user("manager@company.com", "manager", "admin")

# Employees (all 1234)
employees = [
 "abby.gingell@wageflow.com","alex.white@wageflow.com","george.brown@wageflow.com",
 "ashley.harold@wageflow.com","coby.campbell@wageflow.com","christina.mavridis@wageflow.com",
 "hanna.larson@wageflow.com","izzy.rose@wageflow.com","sydney.stewart@wageflow.com","ryan.taylor@wageflow.com",
]
for e in employees:
    upsert_user(e, "employee", "1234")

conn.commit()
cur.close(); conn.close()
print("OK: users upserted into users(email, role, password_hash)")
