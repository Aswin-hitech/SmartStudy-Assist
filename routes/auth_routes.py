from flask import Blueprint, request, jsonify, session
from services.auth_service import create_user, authenticate_user, get_user_by_id

auth_bp = Blueprint("auth_bp", __name__, url_prefix="/api/auth")

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.json
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if not all([name, email, password]):
        return jsonify({"error": "Missing required fields"}), 400

    user = create_user(name, email, password)
    if not user:
        return jsonify({"error": "User with this email already exists"}), 409

    return jsonify({"message": "User registered successfully"}), 201

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    if not all([email, password]):
        return jsonify({"error": "Missing required fields"}), 400

    user = authenticate_user(email, password)
    if not user:
        return jsonify({"error": "Invalid email or password"}), 401

    session["user_id"] = user["_id"]
    return jsonify({
        "message": "Login successful",
        "user": {
            "id": user["_id"],
            "name": user["name"],
            "email": user["email"]
        }
    }), 200

@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.pop("user_id", None)
    return jsonify({"message": "Logged out successfully"}), 200

@auth_bp.route("/me", methods=["GET"])
def me():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401

    user = get_user_by_id(user_id)
    if not user:
        session.pop("user_id", None)
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "user": {
            "id": user["_id"],
            "name": user["name"],
            "email": user["email"],
            "exam_count": user.get("exam_count", 0),
            "average_score": user.get("average_score", 0)
        }
    }), 200
