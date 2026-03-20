from flask import Blueprint, request, jsonify, session
from config import reports_col
from bson import ObjectId
from utils.pdf_generator import generate_report_pdf
from services.auth_service import get_user_by_id

report_bp = Blueprint("report_bp", __name__)

@report_bp.route("/api/reports", methods=["GET"])
def get_user_reports():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    reports = list(reports_col.find({"user_id": user_id}).sort("created_at", -1))
    for r in reports:
        r["_id"] = str(r["_id"])
        # Remove embeddings from listing to save bandwidth
        if "embedding" in r:
            del r["embedding"]

    return jsonify({"reports": reports}), 200

@report_bp.route("/api/reports/<report_id>", methods=["GET"])
def get_report(report_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    report = reports_col.find_one({"_id": ObjectId(report_id), "user_id": user_id})
    if not report:
        return jsonify({"error": "Report not found"}), 404

    report["_id"] = str(report["_id"])
    if "embedding" in report:
        del report["embedding"]

    return jsonify({"report": report}), 200

@report_bp.route("/api/reports/<report_id>/pdf", methods=["GET"])
def get_report_pdf(report_id):
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    report = reports_col.find_one({"_id": ObjectId(report_id), "user_id": user_id})
    if not report:
        return jsonify({"error": "Report not found"}), 404

    user = get_user_by_id(user_id)
    import io
    from flask import send_file
    buffer = io.BytesIO()
    generate_report_pdf(report, user, buffer)
    
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"report_{report_id}.pdf"
    )
