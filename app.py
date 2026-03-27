from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_cors import CORS
from dotenv import load_dotenv
import os

# ================= LOAD ENV =================
load_dotenv()

# ================= INIT APP =================
app = Flask(__name__, template_folder="web", static_folder="static")
CORS(app)

app.secret_key = os.getenv("SECRET_KEY", "fallback_secret_key")


# ================= IMPORT SERVICES =================
from services.llm_services import chat_with_ai

# ================= IMPORT BLUEPRINTS =================
from routes.auth_routes import auth_bp
from routes.exam_routes import exam_bp
from routes.report_routes import report_bp
from routes.upload_routes import upload_bp
from routes.proctoring_routes import proctoring_bp

# ================= REGISTER BLUEPRINTS =================
app.register_blueprint(auth_bp)
app.register_blueprint(exam_bp)
app.register_blueprint(report_bp)
app.register_blueprint(upload_bp)
app.register_blueprint(proctoring_bp)


# ================= BASIC ROUTES =================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat")
def chat():
    if "user_id" not in session: return redirect(url_for("login_page"))
    return render_template("chat.html")


@app.route("/upload")
def upload():
    if "user_id" not in session: return redirect(url_for("login_page"))
    return render_template("generate_qp.html")


@app.route("/test")
def test():
    if "user_id" not in session: return redirect(url_for("login_page"))
    return render_template("test.html")


@app.route("/login")
def login_page():
    return render_template("login.html")


@app.route("/register")
def register_page():
    return render_template("register.html")


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session: return redirect(url_for("login_page"))
    return render_template("dashboard.html")


@app.route("/report_view")
def report_page():
    if "user_id" not in session: return redirect(url_for("login_page"))
    return render_template("report.html")


# ================= CHAT API =================

@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json()
    message = data.get("message", "")

    if not message:
        return jsonify({"error": "Message is required"}), 400

    reply = chat_with_ai(message)
    return jsonify({"reply": reply})




# ================= RUN =================

if __name__ == "__main__":
    app.run(debug=True)