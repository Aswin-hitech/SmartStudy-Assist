import os
from ultralytics import YOLO

# Suppress YOLO output for cleaner console
model = YOLO("yolov8n.pt")

def detect_objects(frame):
    """Run object detection on the frame and alert if a cell phone is found."""
    results = model(frame, verbose=False)
    detections = []

    for r in results:
        for box in r.boxes:
            cls = int(box.cls[0])
            label = model.names[cls]

            if label == "cell phone":
                detections.append("Phone Detected 🚨")

    return detections
