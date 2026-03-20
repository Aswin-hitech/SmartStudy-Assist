import json
import re
from services.llm_services import generate_mcqs_from_syllabus

def clean_text(text):
    if not text:
        return ""
    # Remove extra whitespace, normalize line breaks, extract meaningful text
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
    # Fix trailing commas
    json_str = re.sub(r',\s*\}', '}', json_str)
    json_str = re.sub(r',\s*\]', ']', json_str)
    # Fix missing commas between array elements or object keys
    json_str = re.sub(r'\}\s*\{', '}, {', json_str)
    json_str = re.sub(r'\]\s*\[', '], [', json_str)
    return json_str

def safe_parse_json(output, mode):
    clean_out = str(output).strip()
    # Strip markdown
    if clean_out.startswith("```json"):
        clean_out = clean_out[7:]
    elif clean_out.startswith("```"):
        clean_out = clean_out[3:]
    if clean_out.endswith("```"):
        clean_out = clean_out[:-3]
    clean_out = clean_out.strip()

    # Try direct parse
    try: return json.loads(clean_out)
    except Exception: pass
    
    # Try repaired parse
    try: return json.loads(repair_json(clean_out))
    except Exception: pass

    # Regex Extraction based on mode
    if mode == "test":
        # extract first JSON array [ ... ]
        match = re.search(r'\[.*?\]', clean_out, re.DOTALL)
        if match:
            extracted = match.group(0)
            try: return json.loads(extracted)
            except Exception: pass
            try: return json.loads(repair_json(extracted))
            except Exception: pass
    elif mode == "pdf":
        # extract first JSON object { ... }
        match = re.search(r'\{.*\}', clean_out, re.DOTALL)
        if match:
            extracted = match.group(0)
            try: return json.loads(extracted)
            except Exception: pass
            try: return json.loads(repair_json(extracted))
            except Exception: pass
            
    return None
def normalize_mcq(parsed):
    for q in parsed:
        options = q.get("options", [])

        # Ensure options are clean strings
        q["options"] = [str(opt).strip() for opt in options]

        # Fix answer if string
        if isinstance(q.get("answer"), str):
            try:
                q["answer"] = q["options"].index(q["answer"])
            except:
                q["answer"] = 0  # fallback

        # Ensure valid index
        if not isinstance(q["answer"], int):
            q["answer"] = 0

        q["answer"] = max(0, min(q["answer"], 3))

    return parsed
def validate_exam_json(parsed, mode):
    if mode == "test":
        if not isinstance(parsed, list): return False
        if len(parsed) == 0: return False
        for item in parsed:
            if not isinstance(item, dict): return False
            if 'question' not in item or 'options' not in item or 'answer' not in item: return False
            
            # Normalize options
            if not isinstance(item['options'], list): return False
            if len(item['options']) != 4: return False
            item['options'] = [str(opt) for opt in item['options']]

            # Normalize answer (convert string answer to index)
            if isinstance(item['answer'], str):
                try:
                    # Look for exact match in options
                    item['answer'] = item['options'].index(item['answer'])
                except ValueError:
                    # Fallback or keep as is if not found (validation will fail below)
                    pass

            # Final check on answer type
            if not isinstance(item['answer'], int): return False
            if item['answer'] < 0 or item['answer'] >= 4: return False
            
        return True
    elif mode == "pdf":
        if not isinstance(parsed, dict): return False
        if len(parsed.keys()) == 0: return False
        for k, v in parsed.items():
            if not isinstance(v, list): return False
        return True
    return False

def generate_exam(data):
    raw_syllabus = data.get("syllabus_text", data.get("syllabus", ""))
    syllabus = clean_text(raw_syllabus)
    mcq_count = data.get("mcq_count", 10)
    
    mode = data.get("mode", "test")
    question_pattern = data.get("question_pattern", data.get("model_qp", ""))

    output = ""
    parsed = None
    
    for attempt in range(2):
        retry = (attempt == 1)
        try:
            output = generate_mcqs_from_syllabus(syllabus, question_pattern, mode, mcq_count, retry=retry)
        except Exception as e:
            if retry:
                return {"error": f"AI Generation Failed: {str(e)}"}
            continue
            
        print(f"--- RAW AI OUTPUT (Attempt {attempt+1}, {mode} mode) ---\n{output}\n----------------------------------")

        parsed = safe_parse_json(output, mode)
        if parsed and validate_exam_json(parsed, mode):
            break
        
        parsed = None
        
    if not parsed:
        return {
            "error": "AI returned invalid format after retries. Please try again.",
            "raw_output": output
        }

    if mode == "test":
        return {"mcqs": parsed}
    elif mode == "pdf":
        formatted_paper = format_qp_json_to_text(parsed)
        return {"practice_paper": formatted_paper}

    return {"practice_paper": "Unknown mode"}