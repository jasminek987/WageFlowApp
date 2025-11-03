# src/routes/payslips.py
from flask import Blueprint, request, jsonify, send_file, abort
from io import BytesIO
from src.routes.auth import require_auth
from db import fetch_all, fetch_one
import os

payslips_bp = Blueprint("payslips", __name__)

@payslips_bp.get("/me")
@require_auth
def my_payslips():
    uid = request.user["id"]
    # find employee_id for this user
    emp = fetch_one("SELECT id FROM employees WHERE user_id = %s", (uid,))
    if not emp:
        return jsonify([])

    rows = fetch_all("""
        SELECT id, employee_id,
               to_char(period_start, 'YYYY-MM-DD') AS ps,
               to_char(period_end,   'YYYY-MM-DD') AS pe,
               gross, net
        FROM payslips
        WHERE employee_id = %s
        ORDER BY period_end ASC, id ASC
    """, (emp[0],))

    out = []
    for r in rows:
        pid, eid, ps, pe, gross, net = r
        out.append({
            "id": pid,
            "period": f"{ps} to {pe}",
            "gross": float(gross or 0),
            "net": float(net or 0),
            "pdfUrl": f"/api/payslips/{pid}/pdf"
        })
    return jsonify(out)


@payslips_bp.get("/<int:pid>/pdf")
@require_auth
def payslip_pdf(pid: int):
    """Stream a real PDF for the given payslip id. Employees can only view their own."""
    uid = request.user["id"]
    role = request.user.get("role", "employee")

    row = fetch_one("""
        SELECT p.id,
               e.id                              AS employee_id,
               COALESCE(e.full_name, e.name, u.email) AS employee_name,
               to_char(p.period_start, 'YYYY-MM-DD')  AS ps,
               to_char(p.period_end,   'YYYY-MM-DD')  AS pe,
               p.gross, p.net,
               e.user_id
        FROM payslips p
        JOIN employees e ON e.id = p.employee_id
        JOIN users     u ON u.id = e.user_id
        WHERE p.id = %s
    """, (pid,))
    if not row:
        abort(404)

    (pid_db, emp_id, emp_name, ps, pe, gross, net, payslip_user_id) = row

    # employee can only download their own
    if role != "manager" and payslip_user_id != uid:
        abort(403)

    # --- build a tiny PDF (uses reportlab if available) ---
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        y = 720
        c.setFont("Helvetica", 12)
        c.drawString(72, y,   f"Payslip ID: {pid_db}"); y -= 24
        c.drawString(72, y,   f"Employee: {emp_name}"); y -= 24
        c.drawString(72, y,   f"Period: {ps} to {pe}"); y -= 24
        c.drawString(72, y,   f"Gross Pay: ${float(gross or 0):.2f}"); y -= 24
        c.drawString(72, y,   f"Net Pay:   ${float(net   or 0):.2f}")
        c.showPage(); c.save()
        buffer.seek(0)
        return send_file(
            buffer,
            mimetype="application/pdf",
            as_attachment=False,
            download_name=f"payslip_{pid_db}.pdf"
        )
    except Exception:
        # Fallback: simple text if reportlab isn't present
        content = (
            f"Payslip ID: {pid_db}\n"
            f"Employee: {emp_name}\n"
            f"Period: {ps} to {pe}\n"
            f"Gross Pay: ${float(gross or 0):.2f}\n"
            f"Net Pay: ${float(net or 0):.2f}\n"
        ).encode("utf-8")
        return send_file(BytesIO(content),
            mimetype="application/octet-stream",
            as_attachment=True,
            download_name=f"payslip_{pid_db}.txt")
