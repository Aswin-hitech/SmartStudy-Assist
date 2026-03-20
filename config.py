import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

client = MongoClient(MONGO_URI)
db = client["studyprep"]

users_col = db["users"]
exams_col = db["exams"]
reports_col = db["reports"]