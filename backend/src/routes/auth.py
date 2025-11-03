# src/routes/auth.py
from flask import Blueprint, request, jsonify
import os, time, jwt
from werkzeug.security import check_password_hash
from functools import wraps
from db import fetch_one  # top-level import (db.py sits next to app.py)

auth_bp = Blueprint("auth", __name__)
JWT_SECRET = os.getenv("JWT_SECRET", "devsecret")

def _unauth(msg="unauthorized"):
    return jsonify({"error": msg}), 401

def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        h = request.headers.get("Authorization", "")
        if not h.startswith("Bearer "):
            return _unauth("missing bearer")
        token = h.split(" ", 1)[1].strip()
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        except jwt.PyJWTError:
            return _unauth("invalid or expired token")
        request.user = payload  # {id,email,role}
        return fn(*args, **kwargs)
    return wrapper
@auth_bp.post("/login")
def login():
    data = request.get_json(force=True) or {}
    ident = (data.get("email") or "").strip()
    password = (data.get("password") or "").strip()
    if not ident or not password:
        return _unauth("missing credentials")

    # Your schema has no 'username' and no 'password' column.
    row = fetch_one(
        """
        SELECT id, email, role, password_hash
        FROM users
        WHERE lower(email) = lower(%s)
        LIMIT 1
        """,
        (ident,),
    )
    if not row:
        return _unauth("invalid credentials")

    from werkzeug.security import check_password_hash
    if not row.get("password_hash") or not check_password_hash(row["password_hash"], password):
        return _unauth("invalid credentials")

    payload = {"id": row["id"], "email": row["email"], "role": row["role"], "iat": int(time.time())}
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    return jsonify({"token": token, "role": row["role"]}), 200


@auth_bp.get("/me")
@require_auth
def me():
    row = fetch_one(
        """
        SELECT
          u.id              AS user_id,
          u.email           AS email,
          u.role            AS role,
          e.id              AS employee_id,
          COALESCE(e.full_name, e.name, u.email) AS full_name,
          COALESCE(e.rate, 0) AS rate
        FROM users u
        LEFT JOIN employees e ON e.user_id = u.id
        WHERE u.id = %s
        """,
        (request.user["id"],),
    )
    if not row: return jsonify({"error": "not_found"}), 404
    # return as dict (psycopg2.extras.DictCursor recommended)
    return jsonify(dict(row)), 200


