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

    data["user_id"] = session.get("user_id")
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

    practice_paper = result.get("practice_paper")
    if not practice_paper:
        return jsonify({"error": "Failed to generate practice paper content."}), 500

    buffer = io.BytesIO()
    generate_pdf(practice_paper, buffer)
    
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
        return jsonify({"error": "No active exam"}), 400

    # ✅ VALIDATION
    if len(user_answers) != len(current_exam):
        return jsonify({"error": "Answer count mismatch"}), 400

    for ans in user_answers:
        if not isinstance(ans, int):
            return jsonify({"error": "Invalid answer format"}), 400

    from services.report_service import evaluate_exam
    from routes.proctoring_routes import state

    status_data = state.get_status()
    warning_count = status_data.get("warning_count", 0)
    position_changes = status_data.get("position_changes", 0)

    report = evaluate_exam(
        user_id,
        current_exam,
        user_answers,
        warning_count=warning_count,
        position_changes=position_changes
    )

    session.pop("current_exam", None)

    return jsonify({
        "message": "Submitted",
        "report_id": str(report["_id"])
    }), 200
# ================= DSE: LIVE ADAPTIVE SESSION =================

@exam_bp.route("/api/start_exam", methods=["POST"])
def api_start_exam():
    user_id = session.get("user_id")
    if not user_id: return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    syllabus = data.get("syllabus", "General Knowledge")
    mcq_count = data.get("mcq_count", 10)
    initial_difficulty = data.get("difficulty", "Medium")
    
    # Initialize DSE State with user-selected difficulty as starting point
    session["dse_state"] = {
        "syllabus": syllabus,
        "total": mcq_count,
        "progress": 0,
        "current_difficulty": initial_difficulty,
        "consecutive_correct": 0,
        "consecutive_wrong": 0,
        "answers_detailed": []
    }
    
    from services.exam_service import generate_single_mcq
    q = generate_single_mcq(data, difficulty=initial_difficulty)
    if not q: return jsonify({"error": "Failed to generate first question"}), 500
    
    session["dse_current_q"] = q
    return jsonify({
        "question": q,
        "difficulty": initial_difficulty,
        "progress": 0,
        "total": mcq_count
    })

@exam_bp.route("/api/submit_answer", methods=["POST"])
def api_submit_answer():
    user_id = session.get("user_id")
    state = session.get("dse_state")
    current_q = session.get("dse_current_q")
    
    if not user_id or not state or not current_q:
        return jsonify({"error": "Active session not found"}), 400
    
    data = request.get_json()
    user_idx = data.get("answer")
    
    # 1. Score & Update State
    is_correct = (user_idx == current_q["answer"])
    state["answers_detailed"].append({
        "question": current_q["question"],
        "options": current_q["options"],
        "correct_idx": current_q["answer"],
        "user_idx": user_idx,
        "is_correct": is_correct,
        "topic": current_q.get("topic", "General")
    })
    
    # 2. Difficulty Scaling Logic (3-up, 2-down)
    diff = state["current_difficulty"]
    if is_correct:
        state["consecutive_correct"] += 1
        state["consecutive_wrong"] = 0
        if state["consecutive_correct"] >= 3:
            if diff == "Easy": diff = "Medium"
            elif diff == "Medium": diff = "Hard"
            state["consecutive_correct"] = 0
    else:
        state["consecutive_wrong"] += 1
        state["consecutive_correct"] = 0
        if state["consecutive_wrong"] >= 2:
            if diff == "Hard": diff = "Medium"
            elif diff == "Medium": diff = "Easy"
            state["consecutive_wrong"] = 0
            
    state["current_difficulty"] = diff
    state["progress"] += 1
    
    # 3. Check for completion
    if state["progress"] >= state["total"]:
        from services.report_service import evaluate_exam
        from routes.proctoring_routes import state as pstate
        p_data = pstate.get_status()

        report = evaluate_exam(
            user_id, None, None,
            preformed_answers=state["answers_detailed"],
            position_changes=p_data.get("position_changes", 0)
        )
        session.pop("dse_state", None)
        session.pop("dse_current_q", None)
        return jsonify({"status": "finished", "report_id": str(report["_id"])})

    # 4. Generate Next Question (NRG: Pass history)
    from services.exam_service import generate_single_mcq, get_user_history
    history = get_user_history(user_id)
    next_q = generate_single_mcq({"syllabus": state["syllabus"]}, difficulty=diff, history=history)
    
    if not next_q: return jsonify({"error": "Failed to generate next question"}), 500
    
    session["dse_current_q"] = next_q
    session["dse_state"] = state
    
    return jsonify({
        "question": next_q,
        "difficulty": diff,
        "progress": state["progress"],
        "total": state["total"]
    })
