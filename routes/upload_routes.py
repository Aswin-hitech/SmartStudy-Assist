from flask import Blueprint, request, jsonify
from services.ocr_service import extract_text_from_file

upload_bp = Blueprint("upload", __name__)

@upload_bp.route("/api/upload/syllabus", methods=["POST"])
def upload_syllabus():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400
    try:
        text = extract_text_from_file(file, file.filename)
        return jsonify({"text": text}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@upload_bp.route("/api/upload/pattern", methods=["POST"])
def upload_pattern():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400
    try:
        text = extract_text_from_file(file, file.filename)
        return jsonify({"text": text}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
