import json
import re
import random
from services.llm_services import generate_mcqs_from_syllabus, get_llm, reset_ai_metrics
from config import reports_col
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


# ================= BASIC CLEAN =================
def clean_text(text):
    if not text:
        return ""
    return re.sub(r'\s+', ' ', text).strip()

def clean_option(opt):
    opt = str(opt).strip()
    # Remove existing prefixes like "A.", "B.", "1."
    opt = re.sub(r'^[A-D1-4]\.\s*', '', opt)
    return opt


# ================= PATTERN HELPERS =================

def parse_pattern(pattern_text):
    """
    Extracts Part names, question counts, and type hints from pattern text using an LLM.
    Returns: { section_name: {"count": int, "type": str, "marks": int} }
    """
    if not pattern_text:
        return {"Part A": {"count": 10, "type": "MCQ", "marks": 1}}

    try:
        from services.llm_services import get_llm, extract_json
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import StrOutputParser

        llm = get_llm()
        prompt = ChatPromptTemplate.from_template("""Convert the following exam pattern into structured JSON.

Pattern:
{raw_pattern}

Return ONLY valid JSON in this format:
[
  {{"section": "A", "marks": 1, "count": 30}}
]

Rules:
* Extract section name
* Extract marks per question
* Extract number of questions
* If missing, infer reasonably
* Output ONLY JSON, no explanation""")

        chain = prompt | llm | StrOutputParser()
        
        print(f"[PATTERN PARSER] Requesting LLM parsing for: {pattern_text}")
        response = chain.invoke({"raw_pattern": pattern_text})
        print(f"[PATTERN PARSER] LLM Response: {response}")
        
        parsed_list = extract_json(response)
        
        if not parsed_list or not isinstance(parsed_list, list):
            print(f"[PATTERN PARSER ERROR] Invalid LLM output structure: {parsed_list}")
            raise ValueError("Invalid format returned by LLM")
            
        pattern_dict = {}
        for item in parsed_list:
            if "section" not in item or "marks" not in item or "count" not in item:
                continue
                
            sec_name = str(item["section"]).strip()
            if not sec_name.lower().startswith("part") and not sec_name.lower().startswith("section"):
                sec_name = f"Part {sec_name}"
                
            marks = int(item["marks"])
            count = int(item["count"])
            
            if marks <= 1:
                q_type = "MCQ"
            elif marks <= 3:
                q_type = "Short Answer"
            else:
                q_type = "Long Answer"
                
            pattern_dict[sec_name] = {
                "count": count,
                "type": q_type,
                "marks": marks
            }

        if not pattern_dict:
            print("[PATTERN FALLBACK] Using default pattern")
            return {"Part A": {"count": 10, "type": "MCQ", "marks": 1}}
            
        return pattern_dict
        
    except Exception as e:
        print(f"[PATTERN ERROR] {e}")
        return {"Part A": {"count": 10, "type": "MCQ", "marks": 1}}


def cap_question_distribution(pattern_dict, max_total=25):
    """Scales down question counts if they exceed max_total."""
    total = sum(v["count"] for v in pattern_dict.values())

    if total <= max_total:
        return pattern_dict

    print(f"[CAP] Scaling down from {total} to {max_total} questions")
    scale = max_total / total

    new_pattern = {}
    for section, info in pattern_dict.items():
        new_count = max(1, int(info["count"] * scale))
        new_pattern[section] = {"count": new_count, "type": info["type"], "marks": info.get("marks", 1)}

    return new_pattern


# ================= FORMAT PDF =================
def format_qp_json_to_text(qp_json):
    if not isinstance(qp_json, dict):
        return str(qp_json)

    text = ""
    for section, questions in (qp_json.items() if qp_json else {}):
        text += f"=== {section} ===\n\n"

        if not isinstance(questions, list):
            text += str(questions) + "\n\n"
            continue

        q_num = 0
        for q in (questions or []):
            # SAFE: skip corrupted non-dict entries
            if not isinstance(q, dict):
                print(f"[FORMAT WARN] Skipping non-dict item in '{section}': {type(q).__name__}")
                continue

            q_num += 1
            question = q.get('question', 'Invalid Question')
            marks = q.get('marks', '')
            mark_str = f" [{marks} Marks]" if marks else ""

            text += f"Q{q_num}. {question}{mark_str}\n"

            if isinstance(q.get("options"), list):
                for i, opt in enumerate(q["options"]):
                    clean_opt = clean_option(opt)
                    text += f"   {chr(65+i)}. {clean_opt}\n"

            text += "\n"

    return text


# ================= JSON SANITIZATION =================
def _sanitize_raw_json(text):
    """Fix common LLM JSON corruption before parsing."""
    # Remove markdown wrappers
    text = re.sub(r'```(?:json)?', '', text).strip()
    # Remove backticks inside strings (common LLM glitch)
    text = text.replace('`', '')
    # Fix trailing commas before ] or }
    text = re.sub(r',\s*([\]\}])', r'\1', text)
    # Fix missing quotes around keys (e.g. {question: "..."} → {"question": "..."})
    text = re.sub(r'(\{|,)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', text)
    return text


def _try_parse(text):
    """Attempt JSON parse, return None on failure."""
    if not text: return None
    try:
        return json.loads(text)
    except:
        return None


# ================= JSON SAFETY V2 =================
def safe_parse_json_v2(output, mode):
    """
    Robust JSON parser for LLM output.
    Handles:
    - Markdown wrappers
    - Multiple JSON objects (auto-wrap into array)
    - Partial extraction
    - Corrupt formatting
    """

    print("[RAW LLM OUTPUT]", output)

    raw_text = str(output).strip()

    # ================= CLEAN =================
    text = _sanitize_raw_json(raw_text)

    # ================= AUTO-FIX MULTIPLE OBJECTS =================
    if mode == "test":
        # If multiple { } but not wrapped in []
        if text.count("{") > 1 and not text.strip().startswith("["):
            print("[FIX] Wrapping multiple objects into array")
            text = f"[{text}]"

    # ================= TRY DIRECT PARSE =================
    try:
        result = json.loads(text)
        print(f"[PARSE] Direct parse OK, type={type(result).__name__}")
        return result
    except Exception as e:
        print("[PARSE WARN] Direct parse failed:", e)

    # ================= EXTRACT VALID JSON =================
    try:
        if mode == "test":
            # Try extracting array
            start = text.find('[')
            end = text.rfind(']')

            if start != -1 and end != -1 and end > start:
                extracted = text[start:end+1]
                result = json.loads(extracted)
                print("[PARSE] Extracted array parse OK")
                return result

            # Rebuild array from objects
            objs = re.findall(r'\{.*?\}', text, re.DOTALL)
            if objs:
                print("[FIX] Rebuilding JSON array from objects")
                rebuilt = "[" + ",".join(objs) + "]"
                result = _try_parse(rebuilt)
                if result:
                    print("[PARSE] Rebuilt array parse OK")
                    return result

        elif mode == "pdf":
            start = text.find('{')
            end = text.rfind('}')

            if start != -1 and end != -1 and end > start:
                extracted = text[start:end+1]
                result = json.loads(extracted)
                print("[PARSE] Extracted object parse OK")
                return result

    except Exception as e:
        print("[PARSE ERROR] Extraction failed:", e)

    # ================= FINAL FAIL-SAFE RECOVERY =================
    print("[FORCE RETURN] Returning best-effort parsed data")
    objs = re.findall(r'\{.*?\}', text, re.DOTALL)
    if objs:
        try:
            result = json.loads("[" + ",".join(objs) + "]")

            # 🔥 FIX: convert list → dict for PDF mode
            if mode == "pdf":
                return {
                    "Part A": result if isinstance(result, list) else []
                }

            return result
        except:
            pass

    if mode == "pdf":
        return {
            "Part A": [
                {
                    "question": "Unable to parse AI response.",
                    "marks": 1,
                    "type": "Info"
                }
            ]
        }

    return []


# ================= PDF SECTION SANITIZER =================
def sanitize_pdf_sections(parsed):
    """Ensure every section in a PDF parsed dict contains only valid dict entries."""
    if not isinstance(parsed, dict):
        return None

    cleaned = {}
    total_valid = 0
    for section, questions in (parsed.items() if parsed else {}):
        if not isinstance(questions, list):
            print(f"[SANITIZE] Section '{section}' is not a list, skipping")
            continue
        valid_qs = [q for q in questions if isinstance(q, dict) and q.get("question")]
        print(f"[SANITIZE] Section '{section}': {len(valid_qs)}/{len(questions)} valid questions")
        if valid_qs:
            cleaned[section] = valid_qs
            total_valid += len(valid_qs)

    if not cleaned or total_valid == 0:
        return None
    return cleaned


# ================= USER HISTORY =================
def get_user_history(user_id):
    history_list = []
    try:
        reports = reports_col.find({"user_id": user_id}).sort("created_at", -1).limit(5)

        for r in reports:
            for q in (r.get("answers_detailed", []) or []):
                history_list.append(q["question"])

    except Exception as e:
        print("[History Error]", e)

    if not history_list:
        return None

    return "\n".join([f"- {q}" for q in history_list[:50]])


# ================= MCQ NORMALIZATION =================
def normalize_mcq(mcqs):
    for q in (mcqs or []):
        q["options"] = [str(opt).strip() for opt in q.get("options", [])]

        if len(q.get("options", [])) < 4:
            q["options"] = ["Option A", "Option B", "Option C", "Option D"]
            q["answer"] = 0

        if isinstance(q.get("answer"), str):
            # Case-insensitive match against options
            found = False
            ans_lower = q["answer"].strip().lower()
            for i, opt in enumerate(q["options"]):
                if str(opt).strip().lower() == ans_lower:
                    q["answer"] = i
                    found = True
                    break
            if not found:
                print(f"[NORMALIZE WARN] Could not match answer '{q['answer']}' to options, defaulting to 0")
                q["answer"] = 0

        if not isinstance(q.get("answer"), int):
            try:
                q["answer"] = int(q["answer"])
            except (ValueError, TypeError):
                q["answer"] = 0

        q["answer"] = max(0, min(q["answer"], max(0, len(q.get("options", [])) - 1)))

    return mcqs


# ================= VALIDATION =================
def validate_exam_json(parsed, mode):
    if mode == "test":
        if not isinstance(parsed, list) or not parsed:
            return False

        valid_questions = []

        for q in parsed:
            if not isinstance(q, dict):
                continue

            if not q.get("question"):
                continue

            options = q.get("options", [])
            if not isinstance(options, list) or len(options) < 2:
                continue

            answer = q.get("answer", 0)

            # normalize answer index if it's a string
            if isinstance(answer, str):
                try:
                    answer = options.index(answer)
                except:
                    # check for string options that look like int
                    try:
                        answer = int(answer)
                    except:
                        answer = 0

            if not isinstance(answer, int):
                try:
                    answer = int(answer)
                except:
                    answer = 0

            q["answer"] = max(0, min(answer, len(options) - 1))
            valid_questions.append(q)

        return valid_questions if valid_questions else False

    elif mode == "pdf":
        if not isinstance(parsed, dict) or not parsed:
            return False
        # At least one section must have a list of dicts
        for section, questions in parsed.items():
            if isinstance(questions, list):
                if any(isinstance(q, dict) for q in questions):
                    return True
        return False

    return False


# ================= ANSWER FIX (LLM VALIDATOR) =================
def fix_answers_with_llm(mcqs):
    """
    Validates answers using a separate LLM pass for consistency.
    Targets answers not in [0-3] and randomly samples 30% for quality check.
    """
    llm = get_llm()

    prompt = ChatPromptTemplate.from_template("""
You are a Senior Exam Evaluator. Select the MOST accurate answer index.

STRICT RULES:
- Return ONLY the index (0, 1, 2, or 3)
- No explanations or guesswork
- If unsure, return the most logical one

Question: {question}
Options:
0. {opt0}
1. {opt1}
2. {opt2}
3. {opt3}

Index:""")

    chain = prompt | llm | StrOutputParser()

    for idx, q in enumerate(mcqs or []):
        # Policy: Fix if invalid OR 30% random selection for double-check
        current_ans = q.get("answer")
        options = q.get("options", [])
        if len(options) < 1: continue 

        should_validate = current_ans not in range(len(options)) or random.random() < 0.3
        
        if should_validate:
            try:
                res = chain.invoke({
                    "question": q["question"],
                    "opt0": options[0] if len(options) > 0 else "",
                    "opt1": options[1] if len(options) > 1 else "",
                    "opt2": options[2] if len(options) > 2 else "",
                    "opt3": options[3] if len(options) > 3 else "",
                })
                # Regex extraction
                match = re.search(r'\b[0-3]\b', str(res))
                if match:
                    q["answer"] = int(match.group())
            except Exception as e:
                print(f"[VAL ERROR] Question {idx}: {e}")

    return mcqs


# ================= MAIN GENERATION =================
def generate_exam(data):
    reset_ai_metrics() # Reset metrics tracking
    syllabus = clean_text(data.get("syllabus_text", data.get("syllabus", "")))
    mode = data.get("mode", "test")
    mcq_count = data.get("mcq_count", 10)
    difficulty = data.get("difficulty", "Medium")
    pattern = data.get("question_pattern", data.get("model_qp", ""))
    user_id = data.get("user_id")

    history = get_user_history(user_id) if user_id and mode == "test" else None

    parsed = None
    last_output = None

    if mode == "test":
        for attempt in range(2):
            try:
                if "descriptive" in pattern.lower():
                    from services.llm_services import generate_section_questions
                    output = generate_section_questions("Descriptive Questions", mcq_count, syllabus, section_type="Long Answer")
                else:
                    output = generate_mcqs_from_syllabus(
                        syllabus, pattern, mode,
                        mcq_count, retry=attempt,
                        history=history, difficulty=difficulty
                    )
            except Exception as e:
                if attempt == 1:
                    return {"success": False, "error": str(e)}
                continue

            last_output = output

            if isinstance(output, dict) and "MCQs" in output:
                parsed = output["MCQs"]
            elif isinstance(output, list):
                parsed = output
            else:
                parsed = safe_parse_json_v2(output, mode)

            # STRICT JSON VALIDATION BEFORE RETURN
            if not parsed or not isinstance(parsed, list):
                if attempt == 1:
                    return {"success": False, "error": "Invalid LLM output framework format or count mismatch."}
                parsed = None
                continue

            break

        if not parsed:
            return {"success": False, "error": "AI could not compute a strict structural JSON architecture."}

    # ================= FINAL PROCESS: TEST MODE =================
    if mode == "test":
        parsed = normalize_mcq(parsed)
        validated = validate_exam_json(parsed, mode)
        if validated:
            parsed = validated
        else:
            print("[WARNING] Partial validation used — proceeding with cleaned data")

        # LOGGING
        size = len(parsed) if isinstance(parsed, list) else 0
        print(f"[FINAL OUTPUT SIZE] {size}")
        
        parsed = fix_answers_with_llm(parsed) # Run validation layer
        return {"mcqs": parsed}

    # ================= FINAL PROCESS: PDF MODE =================
    if mode == "pdf":
        print("[MODE] PDF Generation - Using Distributed Pipeline")
        
        # 1. Parse and Cap Pattern
        raw_pattern = pattern or "Part A: 10"
        try:
            parsed_pattern = parse_pattern(raw_pattern)
            print("[PATTERN PARSED]", parsed_pattern)
        except Exception as e:
            return {"success": False, "error": "Could not parse exam pattern. Please provide a clearer format like 'Part A: 10 questions of 2 marks'."}
        
        capped_pattern = cap_question_distribution(parsed_pattern, max_total=25)
        
        # 2. Generate per section
        from services.llm_services import generate_section_questions
        
        final_paper_dict = {}
        for section, info in capped_pattern.items():
            if info["count"] <= 0:
                continue
                
            count = info["count"]
            q_type = info["type"]
            marks = info.get("marks", 1)
            
            print(f"[GEN] Generating exactly {count} {q_type} questions for {section}")
            
            # Use structured instruction for the section
            section_instruction = f"{section} (Exactly {count} {q_type} questions, {marks} marks each)"
            
            section_qs = None
            # 🔥 LOCAL SECTION RETRY (Step 6 implementation)
            for s_attempt in range(2):
                section_qs = generate_section_questions(section_instruction, count, syllabus, section_type=q_type)
                if section_qs and len(section_qs) >= count:
                    break
                print(f"[RETRY SECTION] {section} failed count ({len(section_qs) if section_qs else 0}/{count})")
            
            if section_qs:
                # Ensure marks are correct in the final data
                for q in section_qs:
                    if isinstance(q, dict):
                        q["marks"] = marks
                final_paper_dict[section] = section_qs
            else:
                # Minimal fallback for the missing section
                final_paper_dict[section] = [{"question": f"Failed to generate {section}", "marks": marks, "type": "Info"}]

        # 3. Use the merged dict as 'parsed'
        parsed = final_paper_dict

    # ================= PDF MODE RECOVERY & HARDENING =================
    # (Existing pipeline logic follows, now processing the merged dict)

    # STEP 1: Handle invalid raw outputs like True/None/string
    if not isinstance(parsed, dict):

        if isinstance(parsed, (bool, int)) or str(parsed).strip().lower() in ["true", "false", "none", ""]:
            # Initial rejection if it's a primitive garbage value
            print("[REJECT] Invalid LLM output:", parsed)
            parsed = {
                "Part A": [
                    {
                        "question": "AI returned invalid response. Please regenerate.",
                        "marks": 1,
                        "type": "Info"
                    }
                ]
            }
        else:
            print("[FIX] Attempting secondary parse")
            parsed = safe_parse_json_v2(parsed, "pdf")

            # 🔥 FIX: Missing protection after secondary parse
            if not isinstance(parsed, dict):
                print("[FIX FAIL] Secondary parse failed, forcing fallback")
                parsed = {
                    "Part A": [
                        {
                            "question": "Parsing failed after recovery.",
                            "marks": 1,
                            "type": "Info"
                        }
                    ]
                }

    # STEP 2: Fix wrong structure
    if isinstance(parsed, dict):
        if "practice_paper" in parsed and not isinstance(parsed.get("practice_paper"), list):
            print("[FIX] Converting invalid practice_paper format")

            parsed = {
                "Part A": [
                    {
                        "question": str(parsed.get("practice_paper")),
                        "marks": 1,
                        "type": "Info"
                    }
                ]
            }

    # STEP 3: Hard fallback
    if not isinstance(parsed, dict) or not parsed:
        print("[FALLBACK] Creating safe PDF structure")

        parsed = {
            "Part A": [
                {
                    "question": "AI failed to generate valid questions.",
                    "marks": 1,
                    "type": "Info"
                }
            ]
        }

    # STEP 4: Sanitize safely
    cleaned = sanitize_pdf_sections(parsed)

    if not cleaned or not isinstance(cleaned, dict):
        print("[REJECT] Invalid LLM output:", parsed)

        parsed = {
            "Part A": [
                {
                    "question": "Generated data was invalid. Please retry.",
                    "marks": 1,
                    "type": "Info"
                }
            ]
        }
    else:
        parsed = cleaned

    # STEP 5: ORDER QUESTIONS
    for section in parsed:
        if isinstance(parsed[section], list):
            parsed[section] = sorted(
                parsed[section],
                key=lambda q: (
                    int(q.get("marks", 999)) if str(q.get("marks")).isdigit() else 999,
                    0 if str(q.get("type", "")).lower() == "mcq" else 1
                )
            )

    print("[PDF ORDERED SUCCESSFULLY]")

    # STEP 6: FINAL OUTPUT
    return {"practice_paper": format_qp_json_to_text(parsed)}


# ================= SINGLE MCQ =================
def generate_single_mcq(data, difficulty="Medium", history=None):
    syllabus = clean_text(data.get("syllabus_text", data.get("syllabus", "")))
    try:
        output = generate_mcqs_from_syllabus(
            syllabus, "", "test", 1,
            retry=False, history=history, difficulty=difficulty
        )
        # llm_services returns a parsed list directly; handle both cases for safety
        if isinstance(output, list):
            parsed = output
        else:
            parsed = safe_parse_json_v2(output, "test")

        if parsed:
            validated = validate_exam_json(parsed, "test")
            if validated:
                parsed = validated
            
            if isinstance(parsed, list) and len(parsed) > 0:
                parsed = normalize_mcq(parsed)
                # Validate single question too
                parsed = fix_answers_with_llm(parsed)
                return parsed[0]
    except Exception as e:
        print(f"[Single MCQ Error] {e}")
    return None