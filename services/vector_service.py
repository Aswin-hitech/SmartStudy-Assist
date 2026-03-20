from langchain_huggingface import HuggingFaceEmbeddings
from config import reports_col

# Initialize embedding model
embedding_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)


def store_vector(report_doc):
    """
    Stores embedding of report in MongoDB
    """

    text = f"""
    Score: {report_doc.get('score')}
    Weak Topics: {', '.join(report_doc.get('weak_topics', []))}
    Suggestions: {report_doc.get('suggestions')}
    """

    embedding = embedding_model.embed_query(text)

    reports_col.update_one(
        {"_id": report_doc["_id"]},
        {
            "$set": {
                "embedding": embedding
            }
        }
    )