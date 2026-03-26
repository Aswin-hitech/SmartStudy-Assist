import json
import re
from services.llm_services import generate_mcqs_from_syllabus
from config import reports_col

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def format_qp_json_to_text(qp_json):
    if not isinstance(qp_json, dict):
        return str(qp_json)
    
    text = ""
    for section, questions in qp_json.items():
        text += f"=== {section} ===\n\n"
        for idx, q in enumerate(questions):
            marks = q.get('marks', '')
            mark_str = f" [{marks} Marks]" if marks else ""
            text += f"Q{idx+1}. {q.get('question', '')}{mark_str}\n"
            
            if 'options' in q and isinstance(q['options'], list):
                for i, opt in enumerate(q['options']):
                    text += f"   {chr(65+i)}. {opt}\n"
            text += "\n"
        text += "\n"
    return text

def repair_json(json_str):
    json_str = re.sub(r',\s*\}', '}', json_str)
    json_str = re.sub(r',\s*\]', ']', json_str)
    json_str = re.sub(r'\}\s*\{', '}, {', json_str)
    json_str = re.sub(r'\]\s*\[', '], [', json_str)
    return json_str

def safe_parse_json(output, mode):
    clean_out = str(output).strip()
    if clean_out.startswith("```json"):
        clean_out = clean_out[7:]
    elif clean_out.startswith("```"):
        clean_out = clean_out[3:]
    if clean_out.endswith("```"):
        clean_out = clean_out[:-3]
    clean_out = clean_out.strip()

    try: return json.loads(clean_out)
    except Exception: pass
    
    try: return json.loads(repair_json(clean_out))
    except Exception: pass

    if mode == "test":
        match = re.search(r'\[.*?\]', clean_out, re.DOTALL)
        if match:
            extracted = match.group(0)
            try: return json.loads(extracted)
            except Exception: pass
            try: return json.loads(repair_json(extracted))
            except Exception: pass
    elif mode == "pdf":
        match = re.search(r'\{.*\}', clean_out, re.DOTALL)
        if match:
            extracted = match.group(0)
            try: return json.loads(extracted)
            except Exception: pass
            try: return json.loads(repair_json(extracted))
            except Exception: pass
            
    return None

def get_user_history(user_id):
    """Fetches the last 5 exam questions for the user to prevent repetition."""
    history_list = []
    try:
        query = {"user_id": user_id}
        reports = reports_col.find(query).sort("created_at", -1).limit(5)
        for r in reports:
            for q_detail in r.get("answers_detailed", []):
                history_list.append(q_detail["question"])
    except Exception as e:
        print(f"[History Fetch Error] {e}")
        
    if not history_list:
        return None
    return "\n".join([f"- {q}" for q in history_list[:50]])

def normalize_mcq(parsed):
    for q in parsed:
        options = q.get("options", [])
        q["options"] = [str(opt).strip() for opt in options]
        if isinstance(q.get("answer"), str):
            try:
                q["answer"] = q["options"].index(q["answer"])
            except:
                q["answer"] = 0
        if not isinstance(q["answer"], int):
            q["answer"] = 0
        q["answer"] = max(0, min(q["answer"], 3))
    return parsed

def validate_exam_json(parsed, mode):
    if mode == "test":
        if not isinstance(parsed, list) or len(parsed) == 0: return False
        for item in parsed:
            if not isinstance(item, dict): return False
            if 'question' not in item or 'options' not in item or 'answer' not in item: return False
            if not isinstance(item['options'], list) or len(item['options']) != 4: return False
            if isinstance(item['answer'], str):
                try: item['answer'] = item['options'].index(item['answer'])
                except ValueError: pass
            if not isinstance(item['answer'], int) or item['answer'] < 0 or item['answer'] >= 4: return False
        return True
    elif mode == "pdf":
        if not isinstance(parsed, dict) or len(parsed.keys()) == 0: return False
        for k, v in parsed.items():
            if not isinstance(v, list): return False
        return True
    return False

def generate_exam(data):
    raw_syllabus = data.get("syllabus_text", data.get("syllabus", ""))
    syllabus = clean_text(raw_syllabus)
    mcq_count = data.get("mcq_count", 10)
    mode = data.get("mode", "test")
    difficulty = data.get("difficulty", "Medium")  # Bug Fix #2: extract and thread difficulty
    question_pattern = data.get("question_pattern", data.get("model_qp", ""))
    user_id = data.get("user_id")

    # NRG: Memory-Aware Generation
    history = None
    if user_id and mode == "test":
        history = get_user_history(user_id)

    parsed = None
    last_output = None
    for attempt in range(2):
        retry = (attempt == 1)
        try:
            output = generate_mcqs_from_syllabus(
                syllabus, question_pattern, mode, mcq_count,
                retry=retry, history=history, difficulty=difficulty
            )
        except Exception as e:
            if retry: return {"error": f"AI Generation Failed: {str(e)}"}
            continue

        last_output = output
        print(f"--- LLM OUTPUT (Attempt {attempt+1}, type={type(output).__name__}) ---")

        # Bug Fix #5: llm_services now returns parsed objects directly.
        # Only call safe_parse_json if output is still a raw string.
        if isinstance(output, (list, dict)):
            parsed = output
        else:
            parsed = safe_parse_json(output, mode)

        if parsed and validate_exam_json(parsed, mode):
            break
        parsed = None

    if not parsed:
        print("[ERROR] LLM Output Failed:", last_output)

        if mode == "test":
            fallback = [{
                "question": "Sample fallback question due to generation failure",
                "options": ["A", "B", "C", "D"],
                "answer": 0,
                "topic": "General"
            }]
            return {"mcqs": fallback}
        
        return {"practice_paper": "AI failed to generate paper. Please try again."}
    if mode == "test": return {"mcqs": parsed}
    return {"practice_paper": format_qp_json_to_text(parsed)}

def generate_single_mcq(data, difficulty="Medium", history=None):
    """Generates a single MCQ at a specific difficulty level for the DSE engine."""
    raw_syllabus = data.get("syllabus_text", data.get("syllabus", ""))
    syllabus = clean_text(raw_syllabus)

    try:
        # Bug Fix #3: use the proper difficulty kwarg instead of string-appending to syllabus
        output = generate_mcqs_from_syllabus(
            syllabus, "", "test", 1,
            retry=False, history=history, difficulty=difficulty
        )
        # llm_services returns a parsed list directly; handle both cases for safety
        if isinstance(output, list):
            parsed = output
        else:
            parsed = safe_parse_json(output, "test")

        if parsed and isinstance(parsed, list) and len(parsed) > 0:
            return normalize_mcq(parsed)[0]
    except Exception as e:
        print(f"[Single MCQ Error] {e}")
    return None