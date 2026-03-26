import cv2
import os
from services.proctoring.object_detector import model  # Use the shared YOLO model

# Global variables for app.py /api/head_status
head_status = "Center"
head_warnings = 0

# Thresholds for head position (fraction of frame width)
_LEFT_THRESHOLD = 0.38
_RIGHT_THRESHOLD = 0.62

def _get_head_position(box_center_x, frame_width):
    """Classify head orientation based on the bounding box horizontal center."""
    ratio = box_center_x / frame_width
    if ratio < _LEFT_THRESHOLD:
        return "Left"
    elif ratio > _RIGHT_THRESHOLD:
        return "Right"
    return "Center"

def analyze_frame(frame):
    """
    Proctoring engine using YOLOv8 for person detection and head orientation.
    Returns: (annotated_frame, status_text, head_position)
    """
    global head_status, head_warnings
    
    current_head_pos = "Unknown"
    status = "Proctoring Active"
    
    try:
        h, w, _ = frame.shape
        
        # Run YOLO detection for 'person' (cls 0) and 'cell phone' (cls 67)
        # Using a list of classes to filter if supported, otherwise filter post-run
        results = model(frame, verbose=False)
        
        found_persons = []
        found_phones = False
        
        for r in results:
            for box in r.boxes:
                cls = int(box.cls[0])
                label = model.names[cls]
                
                # Get coords
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                
                if label == "person":
                    found_persons.append(box)
                    # Draw subtle box for face area (top 1/3 of person)
                    head_h = (y2 - y1) // 3
                    cv2.rectangle(frame, (x1, y1), (x2, y1 + head_h), (0, 255, 0), 2)
                
                if label == "cell phone":
                    found_phones = True
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
                    cv2.putText(frame, "Phone Detected", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        # Head position logic based on the detected person
        if len(found_persons) == 1:
            box = found_persons[0]
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            box_center_x = (x1 + x2) // 2
            current_head_pos = _get_head_position(box_center_x, w)
            head_status = current_head_pos
        else:
            current_head_pos = "Unknown"
            head_status = "Not Found"

        # Update warnings is handled by the caller (ProctoringState)
        # But we sync head_status for the /api/head_status route in app.py
        
        return frame, status, current_head_pos

    except Exception as e:
        print(f"[YOLO Proctoring Error] {e}")
        return frame, "Proctoring Error", "Unknown"
