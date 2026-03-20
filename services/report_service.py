from services.llm_services import get_llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from config import reports_col
from services.vector_service import store_vector
import json
from datetime import datetime

def evaluate_exam(user_id, mcqs, user_answers):
    total = len(mcqs)
    score = 0
    topic_performance = {}

    for i, mcq in enumerate(mcqs):
        correct_ans_idx = mcq.get("answer")
        # Ensure answers match length. If user skipped, answer might be None
        user_ans = user_answers[i] if i < len(user_answers) else None
        
        topic = mcq.get("topic", "General")
        if topic not in topic_performance:
            topic_performance[topic] = {"correct": 0, "total": 0}
            
        topic_performance[topic]["total"] += 1

        if user_ans == correct_ans_idx:
            score += 1
            topic_performance[topic]["correct"] += 1

    percentage = (score / total * 100) if total > 0 else 0

    # Categorize strong and weak topics based on > 50% accuracy threshold
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

Given the performance of a student:
Score: {score}/{total}
Strong Topics: {strong_topics}
Weak Topics: {weak_topics}

Provide concise, actionable suggestions for improvement focusing on the weak topics. Keep it under 50 words.
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
        "suggestions": suggestions,
        "created_at": datetime.utcnow()
    }

    # Insert into MongoDB
    result = reports_col.insert_one(report_data)
    report_data["_id"] = result.inserted_id

    # Store vector embedding
    store_vector(report_data)
    
    # Update user stats
    from services.auth_service import update_exam_stats
    update_exam_stats(user_id, percentage)

    return report_data