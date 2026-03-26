from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
import os
import json
import hashlib
import re

load_dotenv()


# ================= LLM =================
def get_llm():
    return ChatGroq(
        groq_api_key=os.getenv("GROQ_API_KEY"),
        model_name=os.getenv("GROQ_MODEL"),
        temperature=0.3  # same as yours (no change in behavior)
    )


# ================= CHAT =================
def chat_with_ai(message):
    llm = get_llm()

    prompt = ChatPromptTemplate.from_template("""
You are an expert AI tutor.

Explain clearly, simply, and correctly.
Avoid unnecessary complexity.

Question:
{question}
""")

    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"question": str(message)})


# ================= HELPERS =================
def extract_json(text):
    try:
        import re

        text = text.replace("```json", "").replace("```", "")

        if "[" in text:
            text = text[text.index("["):]

        if "]" in text:
            text = text[:text.rindex("]") + 1]

        return json.loads(text)

    except Exception as e:
        print("[JSON ERROR]", e)
        return None

def extract_json_object(text):
    try:
        import re

        # 🔥 remove markdown wrappers
        text = text.replace("```json", "").replace("```", "")

        # 🔥 remove leading explanation
        if "{" in text:
            text = text[text.index("{"):]

        # 🔥 remove trailing garbage
        if "}" in text:
            text = text[:text.rindex("}") + 1]

        return json.loads(text)

    except Exception as e:
        print("[JSON OBJECT ERROR]", e)
        return None


def is_valid_mcq(q):
    try:
        if not q.get("question"):
            return False

        if len(q.get("options", [])) != 4:
            return False

        if not isinstance(q.get("answer"), int):
            return False

        if not (0 <= q["answer"] <= 3):
            return False

        correct_option = q["options"][q["answer"]]

        if not correct_option or len(correct_option.strip()) < 2:
            return False

        return True
    except:
        return False


def remove_duplicates(mcqs):
    seen = set()
    unique = []

    for q in mcqs:
        key = hashlib.md5(q["question"].lower().encode()).hexdigest()
        if key not in seen:
            seen.add(key)
            unique.append(q)

    return unique


def diversify_by_topic(mcqs, target_count):
    used_topics = set()
    result = []

    for q in mcqs:
        topic = q.get("topic", "").lower()
        if topic not in used_topics:
            used_topics.add(topic)
            result.append(q)

        if len(result) >= target_count:
            break

    return result


# ================= MCQ GENERATION =================

def generate_mcqs_from_syllabus(
    syllabus,
    model_qp,
    mode,
    mcq_count=10,
    retry=0,
    history=None,
    difficulty="Medium"
):

    syllabus = str(syllabus)
    difficulty = str(difficulty or "Medium")
    history = history or []

    llm = get_llm()

    difficulty_map = {
        "Easy": "simple, direct, basic concept questions",
        "Medium": "application-based, moderate reasoning questions",
        "Hard": "advanced, tricky, competitive exam level questions"
    }

    difficulty_instruction = difficulty_map.get(difficulty, difficulty_map["Medium"])

    # ================= TEST MODE =================
    if mode == "test":

        prompt = ChatPromptTemplate.from_template("""
You are a HIGH-QUALITY EXAM QUESTION SETTER.

GOAL:
Generate DIVERSE, NON-REPETITIVE, REALISTIC MCQs.

SYLLABUS:
{syllabus}

DIFFICULTY:
{difficulty_instruction}

PREVIOUS QUESTIONS (DO NOT REPEAT SIMILAR IDEAS):
{history}

IMPORTANT RULES:

1. Generate EXACTLY {mcq_count} UNIQUE questions

2. DIVERSITY (VERY IMPORTANT):
- Each question must test a DIFFERENT concept

3. OPTIONS:
- Exactly 4 meaningful options
- Only ONE correct answer

OUTPUT JSON ONLY:

[
  {{
    "question": "...",
    "options": ["...", "...", "...", "..."],
    "answer": 0,
    "topic": "..."
  }}
]
""")

        chain = prompt | llm | StrOutputParser()

        raw_output = chain.invoke({
            "syllabus": syllabus,
            "mcq_count": mcq_count,
            "difficulty_instruction": difficulty_instruction,
            "history": history[:15]
        })

        print("[LLM OUTPUT]", raw_output)

        parsed = extract_json(raw_output)

        if parsed:
            parsed = [q for q in parsed if is_valid_mcq(q)]
            parsed = remove_duplicates(parsed)
            parsed = diversify_by_topic(parsed, mcq_count)

            if len(parsed) >= mcq_count:
                return parsed[:mcq_count]

        # 🔁 RETRY (same logic, just visible)
        if retry < 2:
            print("[RETRYING...]")
            return generate_mcqs_from_syllabus(
                syllabus,
                model_qp,
                mode,
                mcq_count,
                retry=retry + 1,
                history=history,
                difficulty=difficulty
            )

        # 🔥 FINAL SAFE FALLBACK
        print("[FALLBACK USED]")
        return [{
            "question": "Fallback question due to AI failure",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "answer": 0,
            "topic": "General"
        }]

    # ================= PDF MODE =================
    else:

        prompt = ChatPromptTemplate.from_template("""
You are a UNIVERSITY QUESTION PAPER SETTER.

SYLLABUS:
{syllabus}

PATTERN:
{model_qp}

RULES:
- Questions must match syllabus
- Maintain academic structure

RETURN STRICT JSON:

{{
  "Part A": [
    {{
      "question": "...",
      "marks": 2,
      "type": "Short Answer"
    }},
    {{
      "question": "...",
      "marks": 1,
      "type": "MCQ",
      "options": ["A", "B", "C", "D"],
      "answer": 0
    }}
  ]
}}
""")

        chain = prompt | llm | StrOutputParser()

        raw_output = chain.invoke({
            "syllabus": syllabus,
            "model_qp": model_qp
        })

        print("[PDF OUTPUT]", raw_output)

        parsed = extract_json_object(raw_output)

        if parsed:
            return parsed

        # 🔥 SAFE FALLBACK (prevents KeyError)
        return {
            "practice_paper": "AI failed to generate paper. Please try again."
        }