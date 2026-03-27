from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
import os
import json
import hashlib
import re

load_dotenv()


# ================= METRICS TRACKER =================
AI_METRICS = {
    "input_tokens": 0,
    "output_tokens": 0,
    "total_tokens": 0,
    "llm_calls": 0,
    "retry_count": 0
}

def reset_ai_metrics():
    AI_METRICS.clear()
    AI_METRICS.update({
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "llm_calls": 0,
        "retry_count": 0
    })

def estimate_tokens(text):
    if not text:
        return 0
    # simple estimate: 1 token ~= 1.3 words (common heuristic for OpenAI/Groq)
    return int(len(str(text).split()) * 1.3) + 1

# ================= LLM =================
def get_llm():
    return ChatGroq(
        groq_api_key=os.getenv("GROQ_API_KEY"),
        model_name=os.getenv("GROQ_MODEL"),
        temperature=0.3,
        max_tokens=2000 # 🔥 HARD LIMIT to prevent truncation and align with Groq
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

    # Track input tokens
    AI_METRICS["input_tokens"] += estimate_tokens(str(message))
    AI_METRICS["llm_calls"] += 1

    chain = prompt | llm | StrOutputParser()
    response = chain.invoke({"question": str(message)})

    # Track output tokens
    AI_METRICS["output_tokens"] += estimate_tokens(response)
    AI_METRICS["total_tokens"] = AI_METRICS["input_tokens"] + AI_METRICS["output_tokens"]

    return response


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


def is_relevant_to_syllabus(question, syllabus):
    keywords = syllabus.lower().split()
    q = question.lower()
    # Accept if at least one meaningful keyword exists
    return any(word in q for word in keywords if len(word) > 3)


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

def generate_mcqs_from_syllabus(syllabus, model_qp, mode="test", mcq_count=10, retry=False, history=None, difficulty="Medium"):
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
        AI_METRICS["llm_calls"] += 1
        if retry:
            AI_METRICS["retry_count"] += 1

        prompt = ChatPromptTemplate.from_template("""
You are an advanced question generation engine. Your output will be directly parsed by a strict JSON parser in a production system. Any formatting error will break the system.

---

# 🎯 TASK

Generate an exam strictly based on the given syllabus and pattern.

---

# 📥 INPUT

* Syllabus: {syllabus}
* Pattern: {pattern}
* MCQ Count: {mcq_count}
* Difficulty: {difficulty_instruction}
* Previous Questions to Avoid: {history}

---

# ⚠️ STRICT OUTPUT RULES (MANDATORY)

1. Output ONLY valid JSON — no explanation, no markdown, no extra text.
2. Follow this EXACT structure:

{{
"MCQs": [
{{
"question": "string",
"marks": 1,
"type": "MCQ",
"options": ["string", "string", "string", "string"],
"answer": 0,
"topic": "string"
}}
]
}}

---

# 🚫 NEVER DO THESE (CRITICAL)

* Do NOT output malformed JSON
* Do NOT miss commas or brackets
* Do NOT use formats like ["A"] "text"
* Do NOT include labels like A., B., C., D. inside options
* Do NOT generate more or fewer than {mcq_count} questions
* Do NOT generate duplicate questions
* Do NOT generate generic/general knowledge questions
* Do NOT ignore syllabus context

---

# ✅ CONTENT RULES

* CRITICAL CONSTRAINT (HARD RULE): Every question MUST explicitly reference or relate to concepts from this syllabus: {syllabus}
* If a question is unrelated to this syllabus (e.g., math, GK, etc.), it is INVALID.
* You MUST internally reject and regenerate until ALL questions strictly match the syllabus domain.
* DO NOT generate ANY question outside this domain.
* Cover different topics evenly
* Maintain conceptual + application-based questions
* Avoid repetition in concepts and wording
* Ensure answers are correct and index-based (0–3)

---

# 🔁 SELF-VALIDATION (VERY IMPORTANT)

Before outputting, internally verify:

✔ JSON is syntactically valid
✔ Total questions == {mcq_count}
✔ Each question has exactly 4 options
✔ No duplicate questions
✔ All questions match syllabus

If ANY condition fails → REGENERATE internally until correct.

---

# 🚀 OUTPUT MODE

Return ONLY the final valid JSON.

No explanations. No notes. No extra characters.
""")

        # Track input tokens
        input_data = {
            "syllabus": syllabus,
            "pattern": model_qp,
            "mcq_count": mcq_count,
            "difficulty_instruction": difficulty_instruction,
            "history": history[:15]
        }
        AI_METRICS["input_tokens"] += estimate_tokens(str(input_data))

        chain = prompt | llm | StrOutputParser()

        raw_output = chain.invoke(input_data)

        # Track output tokens
        AI_METRICS["output_tokens"] += estimate_tokens(raw_output)
        AI_METRICS["total_tokens"] = AI_METRICS["input_tokens"] + AI_METRICS["output_tokens"]

        print("[LLM OUTPUT]", raw_output)

        parsed = extract_json(raw_output) or []

        if parsed:
            # 🔧 FIX 1: Relaxed filtering (DO NOT OVER-REJECT)
            filtered = [q for q in (parsed or []) if is_valid_mcq(q)]

            # If too strict, fallback to original parsed or check relevance
            # (Keeping relevance check but making it non-fatal for counts)
            syllabus_relevant = [q for q in filtered if is_relevant_to_syllabus(q["question"], syllabus)]
            
            if len(syllabus_relevant) < int(mcq_count * 0.6):
                print("[FALLBACK] Using less strict filtering")
                parsed = filtered
            else:
                parsed = syllabus_relevant

            parsed = remove_duplicates(parsed)
            parsed = diversify_by_topic(parsed, mcq_count)

        # 🔧 FIX 2: MODIFY RETRY LOGIC (Accept 60% count)
        if len(parsed) < int(mcq_count * 0.6) and retry < 2:
            print(f"[REJECT] Not enough valid syllabus questions ({len(parsed)}/{mcq_count})")
            return generate_mcqs_from_syllabus(
                syllabus,
                model_qp,
                mode,
                mcq_count,
                retry=retry + 1,
                history=history,
                difficulty=difficulty
            )

        # 🔧 FIX 3: REMOVE HARD FAILURE (FINAL FALLBACK)
        if len(parsed) >= int(mcq_count * 0.6):
            return parsed[:mcq_count]

        print("[FINAL FALLBACK] Returning best effort MCQs")
        if parsed and len(parsed) > 0:
            return parsed[:mcq_count]

        # LAST fallback (dummy safe questions)
        fallback_q = {
            "question": "Fallback Question - Unable to generate from syllabus",
            "marks": 1,
            "type": "MCQ",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "answer": 0,
            "topic": "General"
        }
        return [fallback_q] * mcq_count

    # ================= PDF MODE =================
    else:
        AI_METRICS["llm_calls"] += 1

        prompt = ChatPromptTemplate.from_template("""
You are a STRICT UNIVERSITY QUESTION PAPER GENERATOR.

GOAL:
Generate a structured practice question paper with 100% adherence to section counts.

STRICT GENERATION RULES:
1. COUNT ENFORCEMENT: You MUST generate EXACTLY the number of questions specified per section.
2. DO NOT generate fewer or more.
3. DO NOT skip any section.
4. DO NOT summarize or truncate.
5. If unable to generate exact count, regenerate internally until achieved.

FORMAT:
{{
  "MCQs": [
    {{
      "question": "...",
      "marks": 1,
      "type": "MCQ",
      "options": ["A", "B", "C", "D"],
      "answer": 0
    }}
  ],
  "Five Mark Questions": [
    {{
      "question": "...",
      "marks": 5,
      "type": "Descriptive"
    }}
  ]
}}
STRICT RULES:
1. You MUST generate EXACTLY the number of questions specified in the pattern
2. DO NOT generate fewer or more
3. DO NOT skip any section
4. DO NOT summarize
5. Return ONLY valid JSON (no markdown, no extra text)

SYLLABUS:
{syllabus}

PATTERN:
{model_qp}
""")

        input_data = {
            "syllabus": syllabus,
            "model_qp": model_qp
        }

        AI_METRICS["input_tokens"] += estimate_tokens(str(input_data))

        chain = prompt | llm | StrOutputParser()
        raw_output = chain.invoke(input_data)

        AI_METRICS["output_tokens"] += estimate_tokens(raw_output)
        AI_METRICS["total_tokens"] = AI_METRICS["input_tokens"] + AI_METRICS["output_tokens"]

        print("[PDF OUTPUT]", raw_output)

        parsed = extract_json_object(raw_output)

        if isinstance(parsed, dict):
            return parsed

        # 🔥 DO NOT FALLBACK HERE — let exam_service handle
        raise ValueError("Invalid LLM JSON output")


# ================= DISTRIBUTED GENERATION =================

def generate_section_questions(section_name, count, syllabus, section_type="MCQ"):
    """Generates questions for a single section to prevent LLM truncation."""
    AI_METRICS["llm_calls"] += 1
    
    llm = get_llm()
    
    # 🔥 DYNAMIC PROMPT BASED ON TYPE
    prompt_template = """
You are a STRICT UNIVERSITY QUESTION PAPER GENERATOR.

SECTION GOAL:
Generate EXACTLY {count} questions for section: {section_name}.

STRICT GENERATION RULES:
1. COUNT ENFORCEMENT: You MUST generate EXACTLY {count} questions.
2. SECTION TYPE: The questions MUST be {section_type}.
3. DO NOT generate fewer or more or skip any section.
4. Output ONLY valid JSON.
5. ALL questions MUST be derived ONLY from the provided syllabus.
6. DO NOT generate general knowledge questions.
7. DO NOT hallucinate topics outside syllabus.
8. If syllabus is insufficient, generate conceptual variations from it.
"""

    if section_type == "MCQ":
        prompt_template += """
- Generate {count} MCQs from the syllabus.
- 4 options each
- Only one correct answer
- Concept-based

JSON FORMAT:
[
  {{
    "question": "...",
    "marks": 1,
    "type": "MCQ",
    "options": ["A", "B", "C", "D"],
    "answer": 0
  }}
]
"""
    elif section_type == "Short Answer":
        prompt_template += """
- Generate {count} short answer questions (2 marks).
- No options
- Direct conceptual questions
- Answerable in 2-3 lines

JSON FORMAT:
[
  {{
    "question": "...",
    "marks": 2,
    "type": "Short Answer"
  }}
]
"""
    else:
        prompt_template += """
- Generate {count} long answer questions (10 marks).
- Analytical / explanation / derivation
- Deep understanding required

JSON FORMAT:
[
  {{
    "question": "...",
    "marks": 10,
    "type": "Long Answer"
  }}
]
"""

    prompt_template += """
SYLLABUS:
{syllabus}
"""

    prompt = ChatPromptTemplate.from_template(prompt_template)

    input_data = {
        "section_name": section_name,
        "count": count,
        "syllabus": syllabus,
        "section_type": section_type
    }
    
    AI_METRICS["input_tokens"] += estimate_tokens(str(input_data))
    
    chain = prompt | llm | StrOutputParser()
    try:
        raw_output = chain.invoke(input_data)
        AI_METRICS["output_tokens"] += estimate_tokens(raw_output)
        
        # We need a way to parse this robustly
        # Importing here to avoid circular dependency if needed, 
        # but safe_parse_json_v2 is in exam_service. 
        # Let's use a local simple extractor first.
        from services.exam_service import safe_parse_json_v2, sanitize_pdf_sections
        
        parsed = safe_parse_json_v2(raw_output, "test") # use "test" mode for a flat list
        
        if isinstance(parsed, list):
            return parsed
        return []
    except Exception as e:
        print(f"[SECTION ERROR] {section_name}: {e}")
        return []