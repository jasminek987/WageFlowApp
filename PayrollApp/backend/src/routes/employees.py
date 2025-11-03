# src/routes/employees.py
from flask import Blueprint, jsonify
from .auth import require_auth
from db import fetch_all

employees_bp = Blueprint("employees", __name__)

def _cols(table: str) -> set:
    rows = fetch_all(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = %s
        """,
        (table,),
    )
    # rows may be list[tuple] or list[dict]
    out = set()
    for r in rows:
        out.add(r[0] if isinstance(r, (tuple, list)) else r.get("column_name"))
    return out

@employees_bp.get("")
@employees_bp.get("/")
@require_auth
def list_employees():
    """
    Returns: [{id, name, email, rate}]
    Supports schema with either employees.name or employees.full_name (or both).
    """
    cols = _cols("employees")
    name_expr = None
    if "full_name" in cols and "name" in cols:
        name_expr = "COALESCE(e.full_name, e.name)"
    elif "full_name" in cols:
        name_expr = "e.full_name"
    elif "name" in cols:
        name_expr = "e.name"
    else:
        name_expr = "''::text"

    sql = f"""
        SELECT
          e.id,
          {name_expr} AS name,
          e.email,
          e.rate
        FROM employees e
        ORDER BY e.id
    """
    rows = fetch_all(sql)

    out = []
    for r in rows:
        if isinstance(r, (tuple, list)):
            # id, name, email, rate
            out.append({
                "id": r[0],
                "name": r[1],
                "email": r[2],
                "rate": float(r[3]) if r[3] is not None else 0.0,
            })
        else:
            out.append({
                "id": r.get("id"),
                "name": r.get("name"),
                "email": r.get("email"),
                "rate": float(r.get("rate") or 0),
            })
    return jsonify(out), 200
