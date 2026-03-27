from ultralytics import YOLO

# Load model once
model = YOLO("yolov8n.pt")


def detect_objects(frame):
    """
    Returns:
    {
        "person": bool,
        "phone": bool,
        "boxes": [(label, x1, y1, x2, y2, conf)]
    }
    """
    results = model(frame, verbose=False)

    person_detected = False
    phone_detected = False
    boxes = []

    for r in results:
        for box in r.boxes:
            cls = int(box.cls[0])
            label = model.names[cls]

            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])

            boxes.append((label, x1, y1, x2, y2, conf))

            if label == "person":
                person_detected = True
            elif label == "cell phone":
                phone_detected = True

    return {
        "person": person_detected,
        "phone": phone_detected,
        "boxes": boxes
    }