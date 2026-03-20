from flask import Flask, request, jsonify, render_template, session, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import os

from services.exam_service import generate_exam
from services.llm_services import chat_with_ai
from utils.pdf_generator import generate_pdf

load_dotenv()

app = Flask(__name__, template_folder="web", static_folder="web")
CORS(app)
app.secret_key = os.getenv("SECRET_KEY")


# ================= ROUTES =================

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat")
def chat():
    return render_template("chat.html")

@app.route("/upload")
def upload():
    return render_template("generate_qp.html")

@app.route("/test")
def test():
    return render_template("test.html")


# ================= CHAT =================

@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json()
    message = data.get("message")

    reply = chat_with_ai(message)

    return jsonify({"reply": reply})


from routes.auth_routes import auth_bp
from routes.exam_routes import exam_bp
from routes.report_routes import report_bp
from routes.upload_routes import upload_bp

app.register_blueprint(auth_bp)
app.register_blueprint(exam_bp)
app.register_blueprint(report_bp)
app.register_blueprint(upload_bp)

# ================= ADDITIONAL ROUTES =================
@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/register")
def register_page():
    return render_template("register.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/report_view")
def report_page():
    return render_template("report.html")

# ================= STATIC =================

@app.route("/<path:filename>")
def serve_static(filename):
    return send_from_directory("web", filename)


# ================= RUN =================

if __name__ == "__main__":
    app.run(debug=True)