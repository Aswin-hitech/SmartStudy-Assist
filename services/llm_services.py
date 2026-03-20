from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
import os

load_dotenv()


# ================= LLM =================
def get_llm():
    return ChatGroq(
        groq_api_key=os.getenv("GROQ_API_KEY"),
        model_name=os.getenv("GROQ_MODEL"),
        temperature=0.4
    )


# ================= CHAT =================
def chat_with_ai(message):
    llm = get_llm()

    prompt = ChatPromptTemplate.from_template("""
You are an AI tutor.
Explain clearly and simply.

Question:
{question}
""")

    chain = prompt | llm | StrOutputParser()

    return chain.invoke({"question": str(message)})


# ================= MCQ / QP GENERATION =================
def generate_mcqs_from_syllabus(syllabus, model_qp, mode, mcq_count=10, retry=False):
    
    # -------- SANITIZE INPUTS --------
    syllabus = str(syllabus)
    model_qp = str(model_qp)
    mode = str(mode)
    mcq_count = int(mcq_count)

    llm = get_llm()

    # -------- RETRY INSTRUCTION --------
    retry_instruction = ""
    if retry:
        retry_instruction = "WARNING: Your previous response was INVALID. Return ONLY valid JSON."

    # ================= TEST MODE =================
    if mode == "test":

        prompt = ChatPromptTemplate.from_template("""
You are a university question paper setter.

SYLLABUS:
{syllabus}

Generate EXACTLY {mcq_count} multiple choice questions.

Return ONLY a valid JSON array in this format:
[
  {{
    "question": "string",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "answer": 0,
    "topic": "string"
  }}
]

STRICT RULES:
- Do NOT include explanations
- Do NOT include markdown (no ```json)
- Do NOT include extra text
- Output MUST start with [ and end with ]
- Ensure valid JSON format

{retry_instruction}
""")

        chain = prompt | llm | StrOutputParser()

        return chain.invoke({
            "syllabus": syllabus,
            "mcq_count": mcq_count,
            "retry_instruction": retry_instruction
        })

    # ================= PDF MODE =================
    else:

        prompt = ChatPromptTemplate.from_template("""
You are a university question paper setter.

SYLLABUS:
{syllabus}

QUESTION PAPER PATTERN:
{model_qp}

Generate a structured question paper.

Return ONLY a valid JSON object in this format:
{{
  "Part A": [
    {{
      "question": "string",
      "marks": 2,
      "type": "Short Answer"
    }},
    {{
      "question": "string",
      "marks": 1,
      "type": "MCQ",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "answer": 0
    }}
  ]
}}

STRICT RULES:
- Do NOT include explanations
- Do NOT include markdown
- Do NOT include multiple outputs
- Output MUST start with {{ and end with }}
- Ensure valid JSON format

{retry_instruction}
""")

        chain = prompt | llm | StrOutputParser()

        return chain.invoke({
            "syllabus": syllabus,
            "model_qp": model_qp,
            "retry_instruction": retry_instruction
        })