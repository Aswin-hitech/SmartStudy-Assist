import matplotlib.pyplot as plt
import os
from config import reports_col
from datetime import datetime

# Ensure the directory for graphs exists
GRAPH_DIR = os.path.join("static", "assets", "graphs")
os.makedirs(GRAPH_DIR, exist_ok=True)

def get_user_metrics(user_id, limit=10):
    """Fetch last N reports for a user from MongoDB."""
    try:
        reports = list(reports_col.find({"user_id": user_id}).sort("created_at", 1))
        # Take the last 'limit' reports if there are many
        if len(reports) > limit:
            reports = reports[-limit:]
        
        history = []
        for r in reports:
            history.append({
                "accuracy": r.get("percentage", 0),
                "score": r.get("score", 0),
                "total": r.get("total", 0),
                "tokens": r.get("ai_metrics", {}).get("total_tokens", 0),
                "timestamp": r.get("created_at", datetime.now())
            })
        return history
    except Exception as e:
        print(f"[METRICS FETCH ERROR] {e}")
        return []

def generate_accuracy_graph(history, user_id):
    """Generate Accuracy vs Attempts graph using default matplotlib styles."""
    if not history: return
    
    plt.figure() # Default size
    accuracies = [h["accuracy"] for h in history]
    attempts = list(range(1, len(history) + 1))
    
    plt.plot(attempts, accuracies, marker='o', linestyle='-')
    plt.title("Accuracy Trend")
    plt.xlabel("Attempt Number")
    plt.ylabel("Accuracy (%)")
    plt.grid(True)
    plt.ylim(0, 105)
    
    filepath = os.path.join(GRAPH_DIR, f"accuracy_{user_id}.png")
    plt.savefig(filepath)
    plt.close()

def generate_score_trend_graph(history, user_id):
    """Generate Score vs Attempts graph using default matplotlib styles."""
    if not history: return
    
    plt.figure()
    scores = [h["score"] for h in history]
    attempts = list(range(1, len(history) + 1))
    
    plt.plot(attempts, scores, marker='s', linestyle='-')
    plt.title("Score Trend")
    plt.xlabel("Attempt Number")
    plt.ylabel("Score")
    plt.grid(True)
    
    filepath = os.path.join(GRAPH_DIR, f"score_{user_id}.png")
    plt.savefig(filepath)
    plt.close()

def generate_token_usage_graph(history, user_id):
    """Generate Token Usage vs Attempts graph using default matplotlib styles."""
    if not history: return
    
    plt.figure()
    tokens = [h["tokens"] for h in history]
    attempts = list(range(1, len(history) + 1))
    
    plt.bar(attempts, tokens)
    plt.title("AI Token Usage")
    plt.xlabel("Attempt Number")
    plt.ylabel("Total Tokens")
    plt.grid(True, axis='y')
    
    filepath = os.path.join(GRAPH_DIR, f"tokens_{user_id}.png")
    plt.savefig(filepath)
    plt.close()

def generate_all_graphs(user_id):
    """Fetch history and generate all 3 required graphs."""
    try:
        history = get_user_metrics(user_id)
        if not history:
            return False
            
        generate_accuracy_graph(history, user_id)
        generate_score_trend_graph(history, user_id)
        generate_token_usage_graph(history, user_id)
        return True
    except Exception as e:
        print(f"[GRAPH GENERATION ERROR] {e}")
        return False
