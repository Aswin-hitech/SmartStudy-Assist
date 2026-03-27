# 📘 StudySmart - Measure Your Preparation

An AI-powered exam preparation platform that generates **personalized tests and practice papers** from any syllabus using LLMs, OCR, and intelligent evaluation.

---

## 📑 Table of Contents

1. [Project Overview](#-project-overview)
2. [Key Features](#-key-features)
3. [System Architecture](#-system-architecture)
4. [Project Structure](#-project-structure)
5. [Tech Stack](#-tech-stack)
6. [Installation & Setup](#-installation--setup)
7. [Environment Configuration](#-environment-configuration)
8. [Usage Guide](#-usage-guide)
9. [API Endpoints](#-api-endpoints)
10. [Security Practices](#-security-practices)
11. [Troubleshooting](#-troubleshooting)
12. [Future Enhancements](#-future-enhancements)
13. [Contributors](#-contributors)

---

## 📌 Project Overview

**StudySmart** is an intelligent exam preparation system designed to simulate real-world testing environments.

It enables users to:
- Generate MCQ-based exams from raw syllabus text.
- Upload syllabus or question papers via OCR.
- Create structured university-style question papers.
- Attempt timed exams with AI-powered evaluation.
- Analyze performance and identify weak areas.

---

## ✨ Key Features

- 🧠 **AI-generated MCQs** from syllabus content.
- 📄 **Practice paper generation** (PDF format).
- 🖼️ **OCR support** (Image/PDF → Text extraction).
- ⏱️ **Real-time timed** exam environment.
- 📊 **Performance analytics** (score, weak topics).
- 🤖 **AI-based feedback** & improvement suggestions.
- 🔐 **Secure user authentication** system.
- 📈 **Intelligent diversity** & difficulty handling.

---

## 🏗️ System Architecture

```text
Frontend (HTML + Tailwind + JS)
          ↓
Flask Backend (REST APIs)
          ↓
AI Layer (LangChain + Groq LLM)
          ↓
Service Layer (Exam, OCR, Reports)
          ↓
Database (MongoDB)
          ↓
Vector Storage (Embeddings)
```

---

## 📁 Project Structure

```text
project_root/
│
├── app.py
├── services/
│   ├── proctoring/
│   │   ├── object_detector.py
│   │   └── proctoring_system.py
│   ├── auth_service.py
│   ├── exam_service.py
│   ├── report_service.py
│   ├── vector_service.py
│   ├── llm_services.py
│   └── ocr_service.py
│
├── routes/
│   ├── auth_routes.py
│   ├── exam_routes.py
│   ├── report_routes.py
│   ├── upload_routes.py
│   └── proctoring_routes.py
│
├── models/
│   ├── exam_model.py
│   └── report_model.py
│
├── templates/
│   ├── index.html
│   ├── dashboard.html
│   ├── test.html
│   └── report.html
│
├── static/
│   ├── css/
│   ├── js/
│   └── assets/
│
├── .env
├── requirements.txt
└── README.md
```

---

## ⚙️ Tech Stack

### 🔹 Backend
- Flask (Python)
- REST APIs

### 🔹 AI / ML
- LangChain
- Groq LLM
- HuggingFace Embeddings

### 🔹 Database
- MongoDB

### 🔹 Frontend
- HTML5 & Tailwind CSS
- JavaScript (Vanilla)

### 🔹 OCR
- OCR.space API

---

## 🚀 Installation & Setup

### 1️⃣ Clone Repository

```bash
git clone https://github.com/your-username/studysmart.git
cd studysmart
```

### 2️⃣ Create Virtual Environment

```bash
# Create environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate
```

### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 🔐 Environment Configuration

Create a `.env` file in the root directory:

```env
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=your_model_name
OCR_API_KEY=your_ocr_api_key
MONGO_URI=your_mongodb_uri
SECRET_KEY=your_secret_key
```

---

## ▶️ Usage Guide

Run the application:

```bash
python app.py
```

Open in browser: Navigate to `http://127.0.0.1:5000`

---

## 🌐 API Endpoints

### 🔑 Authentication
| Method | Endpoint |
|--------|----------|
| POST | `/api/auth/register` |
| POST | `/api/auth/login` |
| GET | `/api/auth/me` |

### 🧠 Exam
| Method | Endpoint |
|--------|----------|
| POST | `/api/generate_exam` |
| POST | `/api/submit_exam` |

### 📊 Reports
| Method | Endpoint |
|--------|----------|
| GET | `/api/report/<id>` |

### 📤 Upload
| Method | Endpoint |
|--------|----------|
| POST | `/api/upload/syllabus` |

---

## 🔐 Security Practices

- 🔒 Password hashing using `bcrypt`.
- 🔑 Session-based authentication.
- 🛡️ Environment variables secured via `.env`.
- 🚫 `.gitignore` prevents sensitive data leaks.
- 🔐 Protected backend routes.

---

## 🛠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| AI Generation Fails | Ensure valid Groq API key and check prompt/JSON logic. |
| OCR Not Working | Verify OCR API key and supported file formats (PDF/Image). |
| Module Errors | Run `pip install -r requirements.txt` inside your venv. |

---

## 🔮 Future Enhancements

- 🎯 Dynamic difficulty scaling
- 📚 Adaptive learning based on weak topics
- 📊 Advanced analytics dashboard
- 📄 Structured university-format PDFs
- 🤖 Real-time AI tutor improvements
- 🧠 Improved proctoring (face + tab detection)

---

## 👨‍💻 Contributors

**CSE (AI & ML) | KIT - Kalaignarkarunanidhi Institute of Technology**

- Aswin N
- Melvin Jessan
- Manoj Kumar C

---

> 💡 **Final Note:** StudySmart helps you not just study — but measure your preparation intelligently.
