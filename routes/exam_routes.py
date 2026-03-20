from flask import Blueprint, request, jsonify, session
from services.exam_service import generate_exam
from utils.pdf_generator import generate_pdf

exam_bp = Blueprint("exam_bp", __name__)

@exam_bp.route("/api/generate_exam", methods=["POST"])
def api_generate_exam():
    data = request.get_json()
    
    syllabus = data.get("syllabus_text", data.get("syllabus", ""))
    if not syllabus or not str(syllabus).strip():
        return jsonify({"error": "Syllabus content is empty. Please provide text to generate an exam."}), 400

    mode = data.get("mode", "test")

    if mode == "test":
        if "mcq_count" not in data:
            return jsonify({"error": "mcq_count is required for test mode."}), 400
    elif mode == "pdf":
        question_pattern = data.get("question_pattern", "")
        if not question_pattern or not str(question_pattern).strip():
            return jsonify({"error": "Question pattern is required for Practice PDF mode."}), 400

    result = generate_exam(data)

    if "error" in result:
        return jsonify(result), 400

    if mode == "test":
        # Store generated exam in session to prevent refresh cheat and allow verification
        session["current_exam"] = result["mcqs"]
        return jsonify(result)

    # Practice -> PDF
    import io
    from flask import send_file
    buffer = io.BytesIO()
    generate_pdf(result["practice_paper"], buffer)
    
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name="practice_paper.pdf"
    )

@exam_bp.route("/api/submit_exam", methods=["POST"])
def api_submit_exam():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    user_answers = data.get("answers", [])
    
    current_exam = session.get("current_exam")
    if not current_exam:
        return jsonify({"error": "No active exam found"}), 400

    # We will let report_service handle the evaluation
    from services.report_service import evaluate_exam
    report = evaluate_exam(user_id, current_exam, user_answers)

    # Clear current exam from session
    session.pop("current_exam", None)

    return jsonify({"message": "Exam submitted successfully", "report_id": str(report["_id"])}), 200
