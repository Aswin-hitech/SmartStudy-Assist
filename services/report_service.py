from services.llm_services import get_llm, AI_METRICS, reset_ai_metrics
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from config import reports_col
from services.vector_service import store_vector
from services.auth_service import update_exam_stats
from services.metrics_service import generate_all_graphs
from bson import ObjectId
import json
from datetime import datetime


# ================= ANSWER COMPARISON HELPER =================
def is_correct(user_ans, correct_ans, options):
    """Robust answer comparison that handles int/string mismatch."""
    try:
        if user_ans is None:
            return False

        # Both are ints → direct compare
        if isinstance(user_ans, int) and isinstance(correct_ans, int):
            return user_ans == correct_ans

        # Coerce both to int for comparison
        try:
            return int(user_ans) == int(correct_ans)
        except (ValueError, TypeError):
            pass

        # User sent option text instead of index
        if isinstance(user_ans, str) and isinstance(options, list):
            user_ans_clean = user_ans.strip().lower()
            for i, opt in enumerate(options):
                if str(opt).strip().lower() == user_ans_clean:
                    return i == int(correct_ans)

        return False
    except Exception as e:
        print(f"[EVAL WARN] is_correct() error: {e}")
        return False


def evaluate_exam(user_id, mcqs, user_answers, preformed_answers=None, position_changes=0, **kwargs):
    # Movement threshold: signal suspicious activity if exceeded
    MOVEMENT_THRESHOLD = 15

    if preformed_answers:
        answers_detailed = preformed_answers
        total = len(answers_detailed)
        score = sum(1 for a in answers_detailed if a["is_correct"])
        topic_performance = {}
        for a in answers_detailed:
            t = a.get("topic", "General")
            if t not in topic_performance: topic_performance[t] = {"correct": 0, "total": 0}
            topic_performance[t]["total"] += 1
            if a["is_correct"]: topic_performance[t]["correct"] += 1
    else:
        total = len(mcqs)
        score = 0
        topic_performance = {}
        answers_detailed = []
        for i, mcq in enumerate(mcqs):
            correct_ans_idx = mcq.get("answer")
            user_ans = user_answers[i] if i < len(user_answers) else None
            options = mcq.get("options", [])

            correct = is_correct(user_ans, correct_ans_idx, options)

            # Debug log for mismatches
            if not correct and user_ans is not None:
                print(f"[EVAL DEBUG] Q{i}: user={user_ans}({type(user_ans).__name__}) correct={correct_ans_idx}({type(correct_ans_idx).__name__}) → WRONG")

            # Track detailed results
            answers_detailed.append({
                "question": mcq.get("question"),
                "options": options,
                "correct_idx": correct_ans_idx,
                "user_idx": user_ans,
                "is_correct": correct,
                "topic": mcq.get("topic", "General")
            })

            topic = mcq.get("topic", "General")
            if topic not in topic_performance:
                topic_performance[topic] = {"correct": 0, "total": 0}

            topic_performance[topic]["total"] += 1

            if correct:
                score += 1
                topic_performance[topic]["correct"] += 1

    percentage = (score / total * 100) if total > 0 else 0

    # Categorize topics
    strong_topics = []
    weak_topics = []
    for topic, perf in topic_performance.items():
        if perf["total"] > 0:
            if perf["correct"] / perf["total"] >= 0.5:
                strong_topics.append(topic)
            else:
                weak_topics.append(topic)

    llm = get_llm()
    prompt = ChatPromptTemplate.from_template("""
You are an AI exam evaluator.

Performance Details:
Score: {score}/{total}
Strong Topics: {strong_topics}
Weak Topics: {weak_topics}

Provide concise, actionable suggestions for improvement. Keep it under 60 words.
""")

    chain = prompt | llm | StrOutputParser()
    suggestions = chain.invoke({
        "score": score,
        "total": total,
        "strong_topics": strong_topics,
        "weak_topics": weak_topics
    })

    report_data = {
        "user_id": user_id,
        "score": score,
        "total": total,
        "percentage": percentage,
        "strong_topics": strong_topics,
        "weak_topics": weak_topics,
        "topic_performance": topic_performance,
        "answers_detailed": answers_detailed,
        "suggestions": suggestions,
        "position_changes": position_changes,
        "suspicious_movement": position_changes > MOVEMENT_THRESHOLD,
        "challenge_attempts": 0,
        "challenge_summary": None,
        "ai_metrics": AI_METRICS.copy(), # Store captured AI metrics
        "created_at": datetime.utcnow()
    }

    # Insert into MongoDB
    result = reports_col.insert_one(report_data)
    report_data["_id"] = result.inserted_id

    # Store vector embedding
    store_vector(report_data)
    
    # Update user stats
    update_exam_stats(user_id, percentage)

    # Generate Graphs
    try:
        generate_all_graphs(user_id)
    except Exception as e:
        print(f"[FAIL-SAFE] Graph generation failed: {e}")

    # Reset metrics for next action
    reset_ai_metrics()

    return report_data

def re_evaluate_report(report_id, user_id):
    """
    Acts as a 'Critic' to re-evaluate all incorrect answers in a report.
    Updates the score and status if the system was wrong or the user was right.
    """
    report = reports_col.find_one({"_id": ObjectId(report_id), "user_id": user_id})
    if not report:
        raise ValueError("Report not found")
    
    attempts = report.get("challenge_attempts", 0)
    if attempts >= 3:
        raise ValueError("Maximum 3 challenge attempts reached for this report.")

    wrong_answers = [ans for ans in report.get("answers_detailed", []) if not ans["is_correct"]]
    if not wrong_answers:
        return report # Nothing to re-evaluate

    llm = get_llm()
    prompt = ChatPromptTemplate.from_template("""
You are a Senior Exam Auditor. Below are questions that a student got "Wrong". 
Re-evaluate each one carefully. 

Possible Decisions:
1. "System Correct": The system's answer key is correct. Student is wrong.
2. "User Correct": The student's answer is actually valid or the system's key is wrong.
3. "Ambiguous": The question is flawed or has multiple valid answers.

Data to Re-evaluate:
{wrong_answers_json}

Return your findings in STRICT JSON format:
{{
  "evaluations": [
    {{
      "question_text": "...",
      "decision": "System Correct" | "User Correct" | "Ambiguous",
      "explanation": "Brief reason why"
    }}
  ],
  "summary": "Overall summary of corrections"
}}
""")

    chain = prompt | llm | StrOutputParser()
    try:
        response_text = chain.invoke({"wrong_answers_json": json.dumps(wrong_answers)})
        # Clean potential markdown
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        
        evaluation_data = json.loads(response_text)
    except Exception as e:
        print(f"[RE-EVAL ERROR] Parsing failed: {e}")
        return report

    # Update Logic
    new_answers_detailed = list(report.get("answers_detailed", []))
    corrections_made = 0
    
    for eval_item in evaluation_data.get("evaluations", []):
        for ans in new_answers_detailed:
            if ans["question"] == eval_item["question_text"] and not ans["is_correct"]:
                if eval_item["decision"] == "User Correct":
                    ans["is_correct"] = True
                    ans["challenged"] = True
                    ans["challenge_note"] = eval_item["explanation"]
                    corrections_made += 1
                elif eval_item["decision"] == "Ambiguous":
                    ans["is_ambiguous"] = True
                    ans["challenge_note"] = eval_item["explanation"]

    if corrections_made > 0 or attempts == 0:
        # Recalculate metrics
        new_score = sum(1 for ans in new_answers_detailed if ans.get("is_correct"))
        total = report["total"]
        new_percentage = (new_score / total * 100) if total > 0 else 0
        
        # Update topic performance
        new_topic_perf = {}
        for ans in new_answers_detailed:
            topic = ans.get("topic", "General")
            if topic not in new_topic_perf:
                new_topic_perf[topic] = {"correct": 0, "total": 0}
            new_topic_perf[topic]["total"] += 1
            if ans.get("is_correct"):
                new_topic_perf[topic]["correct"] += 1

        # Recalculate strong/weak topics
        new_strong = []
        new_weak = []
        for topic, perf in new_topic_perf.items():
            if perf["total"] > 0:
                if perf["correct"] / perf["total"] >= 0.5:
                    new_strong.append(topic)
                else:
                    new_weak.append(topic)

        # Simple update for now, let's update everything we can
        update_fields = {
            "score": new_score,
            "percentage": new_percentage,
            "topic_performance": new_topic_perf,
            "strong_topics": new_strong,
            "weak_topics": new_weak,
            "answers_detailed": new_answers_detailed,
            "challenge_attempts": attempts + 1,
            "challenge_summary": evaluation_data.get("summary"),
            "last_challenged_at": datetime.utcnow()
        }
        
        reports_col.update_one({"_id": ObjectId(report_id)}, {"$set": update_fields})
        report.update(update_fields)

    return report