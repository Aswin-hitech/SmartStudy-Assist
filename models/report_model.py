from datetime import datetime


def create_report_schema(user_id, exam_id, analysis):

    return {
        "user_id": user_id,
        "exam_id": exam_id,
        "score": analysis.get("score", 0),
        "total": analysis.get("total", 0),
        "weak_topics": analysis.get("weak_topics", []),
        "suggestions": analysis.get("suggestions", ""),
        "created_at": datetime.utcnow()
    }