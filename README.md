# 📘 StudySmart - Measure Your Preparation

An AI-powered exam preparation platform that generates **personalized tests and practice papers** from any syllabus using LLMs, OCR, and intelligent evaluation.

---

# 🤖 SmartStudy AI – MEASURE YOUR PREPARATION

## 📑 Table of Contents

1. [Project Overview](#project-overview)
2. [Features](#features)
3. [Architecture](#architecture)
4. [Project Structure](#project-structure)
5. [Tech Stack](#tech-stack)
6. [Installation & Setup](#installation--setup)
7. [Configuration](#configuration)
8. [Usage](#usage)
9. [API Endpoints](#api-endpoints)
10. [Screenshots](#screenshots)
11. [Security](#security)
12. [Future Enhancements](#future-enhancements)
13. [Troubleshooting](#troubleshooting)
14. [Contributors](#contributors)

---

## 📌 Project Overview

**StudySmart** is an AI-driven platform that allows users to:

* Generate MCQ-based tests from raw syllabus text
* Upload syllabus/question papers via OCR
* Create structured practice question papers
* Take timed exams with real-time evaluation
* Get AI-powered feedback and performance analysis

It is designed to simulate **real exam environments** and improve learning efficiency.

---

## ✨ Features

* 🧠 AI-generated MCQs from syllabus
* 📄 Practice PDF generation with custom patterns
* 🖼️ OCR support (image/PDF → text extraction)
* ⏱️ Timed exam mode
* 📊 Performance analytics (score, weak topics)
* 🤖 AI feedback for improvement
* 🔐 Secure authentication system
* 💾 Vector embeddings for smart insights

---

## 🏗️ Architecture

```
Frontend (HTML + Tailwind)
        ↓
Flask Backend (API Layer)
        ↓
AI Layer (LLM - Groq via LangChain)
        ↓
Services Layer (Exam, OCR, Reports)
        ↓
Database (MongoDB)
        ↓
Vector Storage (Embeddings)
```

---

## 📁 Project Structure

```
project_root/
│
├── app.py
│
├── services/
│   ├── auth_service.py
│   ├── exam_service.py
│   ├── report_service.py
│   ├── vector_service.py
│   ├── llm_services.py
│   ├── ocr_service.py
│
├── routes/
│   ├── auth_routes.py
│   ├── exam_routes.py
│
├── models/
│   ├── exam_model.py
│   ├── report_model.py
│
├── templates/
│   ├── index.html
│   ├── exam.html
│
├── static/
│   ├── css/
│   ├── js/
│
├── .env
├── requirements.txt
└── README.md
```

---

## ⚙️ Tech Stack

### 🔹 Backend

* Flask
* Python

### 🔹 AI / ML

* LangChain
* Groq LLM
* HuggingFace Embeddings

### 🔹 Database

* MongoDB

### 🔹 Frontend

* HTML
* Tailwind CSS
* JavaScript

### 🔹 OCR

* OCR.space API

---

## 🚀 Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/studysmart.git
cd studysmart
```

---

### 2. Create Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate   # Windows
```

---

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## 🔐 Configuration

Create a `.env` file in root:

```env
GROQ_API_KEY=your_api_key
GROQ_MODEL=your_model
OCR_API_KEY=your_ocr_key
MONGO_URI=your_mongodb_uri
```

---

## ▶️ Usage

Run the application:

```bash
python app.py
```

Then open:

```
http://127.0.0.1:5000
```

---

## 🌐 API Endpoints

### 🔑 Auth

* `POST /api/auth/register`
* `POST /api/auth/login`
* `GET /api/auth/me`

### 🧠 Exam

* `POST /api/generate_exam`
* `POST /api/submit_exam`

---

## 🖼️ Screenshots

*(Add your UI screenshots here)*

---

## 🔐 Security

* Passwords hashed using bcrypt
* Environment variables secured via `.env`
* `.gitignore` prevents secret leaks

---

## 🔮 Future Enhancements

* 🎯 Difficulty-based question generation
* 📚 Topic-wise adaptive learning
* 📊 Advanced analytics dashboard
* 📄 Export to formatted university PDFs
* 🧠 Personalized AI tutor mode
* 📱 Mobile app version

---

## 🛠️ Troubleshooting

### ❌ JSON Parsing Errors

* Ensure AI response is valid JSON
* Check retry logic in backend

### ❌ OCR Issues

* Verify API key
* Ensure file format supported

### ❌ Module Errors

```bash
pip install -r requirements.txt
```

---

## 👨‍💻 Contributors

**Aswin N - CSE(AI&ML) - KIT KALAIGNARKARUNANIDHI INSTITUTE OF TECHNOLOGY**

**MELVIN JESSAN - CSE(AI&ML) - KIT KALAIGNARKARUNANIDHI INSTITUTE OF TECHNOLOGY**

**MANOJ KUMAR C - CSE(AI&ML) - KIT KALAIGNARKARUNANIDHI INSTITUTE OF TECHNOLOGY**

---

## ⭐ Final Note

This project demonstrates:

* Real-world AI integration
* Full-stack system design
* LLM + OCR + backend engineering

---

💡 *StudySmart helps you not just study — but measure your preparation intelligently.*
