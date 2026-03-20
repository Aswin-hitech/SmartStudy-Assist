import matplotlib
matplotlib.use('Agg') # Headless backend
import matplotlib.pyplot as plt
import io

def generate_bar_chart(topic_performance):
    topics = list(topic_performance.keys())
    scores = [perf["correct"] for perf in topic_performance.values()]
    
    plt.figure(figsize=(6, 4))
    plt.bar(topics, scores, color='#4F46E5')
    plt.xlabel("Topics")
    plt.ylabel("Correct Answers")
    plt.title("Topic-wise Performance")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    return buf

def generate_pie_chart(score, total):
    incorrect = total - score
    labels = ['Correct', 'Incorrect']
    sizes = [score, incorrect]
    colors = ['#10B981', '#EF4444']
    
    plt.figure(figsize=(5, 5))
    if total > 0:
        plt.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
    else:
        plt.pie([1], labels=['No Data'], colors=['#E5E7EB'])
    plt.title("Overall Accuracy")
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    return buf

def generate_percentage_meter(percentage):
    plt.figure(figsize=(5, 5))
    
    sizes = [percentage, max(100 - percentage, 0)]
    colors = ['#3B82F6', '#E5E7EB']
    
    plt.pie(sizes, colors=colors, startangle=90, counterclock=False, 
            wedgeprops={"width": 0.3, "edgecolor": 'white'})
    
    plt.text(0, 0, f"{percentage:.1f}%", ha='center', va='center', fontsize=20, fontweight='bold')
    plt.title("Score Percentage")
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    return buf
