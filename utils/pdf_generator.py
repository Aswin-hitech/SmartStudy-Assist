import io
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from utils.chart_generator import generate_bar_chart, generate_pie_chart, generate_percentage_meter

def generate_pdf(text, buffer):
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()
    elements = []

    for line in text.split("\n"):
        elements.append(Paragraph(line, styles["Normal"]))
        elements.append(Spacer(1, 0.2 * inch))

    doc.build(elements)
    buffer.seek(0)
    return buffer

def generate_report_pdf(report, user, buffer):
    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    title_style = styles["Title"]
    elements.append(Paragraph("AI Exam Evaluation Report", title_style))
    elements.append(Spacer(1, 0.2 * inch))

    # Student Info
    h2 = styles["Heading2"]
    normal = styles["Normal"]
    elements.append(Paragraph("Student Information", h2))
    elements.append(Paragraph(f"Name: {user.get('name', 'N/A')}", normal))
    elements.append(Paragraph(f"Email: {user.get('email', 'N/A')}", normal))
    elements.append(Spacer(1, 0.2 * inch))

    # Score Summary
    elements.append(Paragraph("Score Summary", h2))
    score_text = f"Score: {report.get('score')}/{report.get('total')} ({report.get('percentage'):.2f}%)"
    elements.append(Paragraph(score_text, normal))
    elements.append(Spacer(1, 0.2 * inch))

    # Charts
    topic_perf = report.get("topic_performance", {})
    bar_buf = generate_bar_chart(topic_perf)
    pie_buf = generate_pie_chart(report.get("score", 0), report.get("total", 0))
    meter_buf = generate_percentage_meter(report.get("percentage", 0))

    elements.append(Paragraph("Visual Insights", h2))
    
    # Add images
    elements.append(Image(meter_buf, width=3*inch, height=3*inch))
    elements.append(Spacer(1, 0.2 * inch))
    
    bar_img = Image(bar_buf, width=4*inch, height=2.66*inch)
    pie_img = Image(pie_buf, width=3*inch, height=3*inch)
    
    # We can use a table to put them side by side
    chart_table = Table([[bar_img, pie_img]])
    elements.append(chart_table)
    elements.append(Spacer(1, 0.2 * inch))

    # Weak & Strong Topics
    elements.append(Paragraph("Strong Topics", h2))
    strong_topics = ", ".join(report.get("strong_topics", [])) or "None identified"
    elements.append(Paragraph(strong_topics, normal))
    elements.append(Spacer(1, 0.2 * inch))

    # Weak Topics
    elements.append(Paragraph("Weak Topics", h2))
    weak_topics = ", ".join(report.get("weak_topics", [])) or "None identified"
    elements.append(Paragraph(weak_topics, normal))
    elements.append(Spacer(1, 0.2 * inch))

    # AI Suggestions
    elements.append(Paragraph("AI Suggestions & Feedback", h2))
    elements.append(Paragraph(report.get("suggestions", "No suggestions available."), normal))

    doc.build(elements)
    
    # Close internal buffers
    bar_buf.close()
    pie_buf.close()
    meter_buf.close()

    buffer.seek(0)
    return buffer