from config import users_col
from bson import ObjectId
import bcrypt


# ================= REGISTER =================
def create_user(name, email, password):

    if users_col.find_one({"email": email}):
        return None

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    user = {
        "name": name,
        "email": email,
        "password": hashed,
        "exam_count": 0,
        "average_score": 0
    }

    users_col.insert_one(user)
    return user


# ================= LOGIN =================
def authenticate_user(email, password):

    user = users_col.find_one({"email": email})

    if not user:
        return None

    if not bcrypt.checkpw(password.encode(), user["password"]):
        return None

    user["_id"] = str(user["_id"])
    return user


# ================= GET USER =================
def get_user_by_id(user_id):

    user = users_col.find_one({"_id": ObjectId(user_id)})

    if not user:
        return None

    user["_id"] = str(user["_id"])
    return user


# ================= UPDATE STATS =================
def update_exam_stats(user_id, new_score):

    user = users_col.find_one({"_id": ObjectId(user_id)})

    if not user:
        return

    total_exams = user.get("exam_count", 0)
    avg = user.get("average_score", 0)

    new_avg = ((avg * total_exams) + new_score) / (total_exams + 1)

    users_col.update_one(
        {"_id": ObjectId(user_id)},
        {
            "$set": {
                "average_score": round(new_avg, 2)
            },
            "$inc": {
                "exam_count": 1
            }
        }
    )