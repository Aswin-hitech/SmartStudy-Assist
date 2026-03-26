import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")

# --- Internal connection state ---
_client = None
_db = None

def get_db():
    global _client, _db
    if _db is None:
        try:
            _client = MongoClient(
                MONGO_URI,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000
            )
            _db = _client["studyprep"]
            _client.admin.command('ping')
        except Exception as e:
            raise ConnectionError(f"MongoDB connection failed: {e}")
    return _db

class LazyCollection:
    """A proxy that defers connection until a collection method is called."""
    def __init__(self, name):
        self._name = name

    def _get_col(self):
        db = get_db()
        if db is None:
            raise ConnectionError(f"Database connection failed. Cannot access collection '{self._name}'. Check your MONGO_URI and network.")
        return db[self._name]

    def __getattr__(self, name):
        # Forward all method calls and attribute access to the real pymongo collection
        return getattr(self._get_col(), name)

# --- Public API (Legacy support: no change needed in other files) ---
users_col = LazyCollection("users")
exams_col = LazyCollection("exams")
reports_col = LazyCollection("reports")