from datetime import datetime

def create_exam_schema(user_id, mode, mcqs):

    return {
        "user_id": user_id,
        "mode": mode,
        "mcqs": mcqs,
        "answers": {},
        "score": 0,
        "proctor_warnings": 0,
        "created_at": datetime.utcnow()
    }