# src/routes/timesheets.py
from flask import Blueprint, request, jsonify
from .auth import require_auth
from db import fetch_all, fetch_one, execute

timesheets_bp = Blueprint("timesheets", __name__)

def _row(r):
    # r is a RealDictRow from psycopg2.extras
    return {
        "id": r["id"],
        "employeeId": r["employee_id"],
        "weekStart": r["week_start"],
        "weekEnd": None,                   # not in your schema
        "hours": r.get("hours") or 0,
        "status": (r.get("status") or "").lower(),
    }

@timesheets_bp.get("")
@timesheets_bp.get("/")
@require_auth
def list_timesheets():
    """
    GET /api/timesheets             -> all rows (ordered latest first)
    GET /api/timesheets?latest=1    -> one latest row per employee
    """
    latest = request.args.get("latest", "").strip().lower() in ("1", "true", "yes")

    if latest:
        # one latest timesheet per employee by week_start desc (and id as tiebreaker)
        rows = fetch_all(
            """
            SELECT DISTINCT ON (t.employee_id)
                   t.id, t.employee_id, t.week_start, t.hours, t.status
            FROM timesheets t
            ORDER BY t.employee_id, t.week_start DESC, t.id DESC
            """
        )
    else:
        rows = fetch_all(
            """
            SELECT id, employee_id, week_start, hours, status
            FROM timesheets
            ORDER BY week_start DESC, id DESC
            """
        )

    return jsonify([_row(r) for r in rows])

@timesheets_bp.get("/me")
@require_auth
def my_timesheets():
    uid = request.user["id"]
    rows = fetch_all(
        """
        SELECT t.id, t.employee_id, t.week_start, t.hours, t.status
        FROM timesheets t
        JOIN employees e ON e.id = t.employee_id
        JOIN users u      ON u.id = e.user_id
        WHERE u.id = %s
        ORDER BY t.week_start DESC, t.id DESC
        """,
        (uid,),
    )
    items = [{"id": r[0], "employeeId": r[1], "weekStart": str(r[2]), "hours": float(r[3]), "status": r[4]} for r in rows]
    return jsonify(items)

# ---- Approve timesheet ----
@timesheets_bp.patch("/<int:ts_id>/approve")
@timesheets_bp.patch("/<int:ts_id>/approve/")
@timesheets_bp.post("/<int:ts_id>/approve")
@timesheets_bp.post("/<int:ts_id>/approve/")
@require_auth
def approve_timesheet(ts_id: int):
    found = fetch_one("SELECT id, status FROM timesheets WHERE id = %s", (ts_id,))
    if not found:
        return jsonify({"error": "not_found"}), 404

    if (found["status"] or "").upper() == "APPROVED":
        return jsonify({"ok": True, "already": True})

    execute("UPDATE timesheets SET status = 'APPROVED' WHERE id = %s", (ts_id,))
    return jsonify({"ok": True})
