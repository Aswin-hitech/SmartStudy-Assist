import cv2
import time
from collections import deque, Counter
from services.proctoring.object_detector import detect_objects


# ================= FACE DETECTOR =================
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
)


# ================= HEAD POSITION =================
LEFT_T, RIGHT_T = 0.35, 0.65
UP_T, DOWN_T = 0.35, 0.65


def get_head_position(x, y, w, h, frame_w, frame_h, movement_speed):
    cx, cy = x + w // 2, y + h // 2

    hr = cx / frame_w
    vr = cy / frame_h

    # 🔥 BASE POSITION
    if hr < 0.40:
        pos = "Left"
    elif hr > 0.60:
        pos = "Right"
    elif vr < 0.40:
        pos = "Up"
    elif vr > 0.60:
        pos = "Down"
    else:
        pos = "Center"

    # 🔥 NEW: detect subtle turning (IMPORTANT)
    if pos == "Center" and movement_speed > 12:
        if cx < frame_w * 0.48:
            pos = "Left"
        elif cx > frame_w * 0.52:
            pos = "Right"

    return pos

# ================= TRACKERS =================
class MovementTracker:
    def __init__(self):
        self.history = deque(maxlen=20)

    def update(self, x, y):
        self.history.append((x, y))

    def speed(self):
        if len(self.history) < 5:
            return 0

        dist = 0
        for i in range(1, len(self.history)):
            dx = self.history[i][0] - self.history[i - 1][0]
            dy = self.history[i][1] - self.history[i - 1][1]
            dist += (dx**2 + dy**2) ** 0.5

        return dist / len(self.history)


class SuspicionTracker:
    def __init__(self):
        self.head_history = deque(maxlen=20)

        self.current_status = "Normal"
        self.start_time = None

        # REAL-TIME thresholds (seconds)
        self.look_time = 1.5
        self.phone_time = 1.0
        self.absent_time = 2.0

        self.last_seen = time.time()
        self.look_start = None
        self.phone_start = None

    def smooth_head(self):
        if not self.head_history:
            return "Unknown"
        return Counter(self.head_history).most_common(1)[0][0]

    def update(self, head, phone, person):
        now = time.time()
        self.head_history.append(head)
        smooth = self.smooth_head()

        # PERSON
        if person:
            self.last_seen = now

        # PHONE
        if phone:
            if not self.phone_start:
                self.phone_start = now
        else:
            self.phone_start = None

        # LOOK AWAY
        if smooth not in ["Center", "Unknown"]:
            if not self.look_start:
                self.look_start = now
        else:
            self.look_start = None

        # STATUS LOGIC
        if self.phone_start and (now - self.phone_start > self.phone_time):
            status = "Phone Detected"
        elif now - self.last_seen > self.absent_time:
            status = "Person Missing"
        elif self.look_start and (now - self.look_start > self.look_time):
            status = "Looking Away"
        else:
            status = "Normal"

        if status != self.current_status:
            self.current_status = status
            self.start_time = now if status != "Normal" else None

        return status, {
            "status": status,
            "duration": (now - self.start_time) if self.start_time else 0
        }


# ================= MAIN =================
def analyze_frame(frame, tracker, movement):
    try:
        h, w, _ = frame.shape

        # ===== OBJECT DETECTION =====
        detections = detect_objects(frame)

        # Draw boxes
        for label, x1, y1, x2, y2, conf in detections["boxes"]:
            color = (0, 255, 0) if label == "person" else (0, 0, 255)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        # ===== FACE =====
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(60, 60))

        head = "Unknown"

        if len(faces) > 0:
            faces = sorted(faces, key=lambda x: x[2]*x[3], reverse=True)
            x, y, fw, fh = faces[0]

            cv2.rectangle(frame, (x, y), (x+fw, y+fh), (255, 0, 0), 2)

            speed = movement.speed()

            head = get_head_position(x, y, fw, fh, w, h, speed)

            movement.update(x + fw//2, y + fh//2)

            if movement.speed() > 20:
                cv2.putText(frame, "Rapid Movement!", (20, 120),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        # ===== TRACKER =====
        status, data = tracker.update(
            head,
            detections["phone"],
            detections["person"]
        )

        # ===== UI =====
        color = (0, 255, 0) if status == "Normal" else (0, 0, 255)

        cv2.putText(frame, f"Status: {status}", (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        cv2.putText(frame, f"Head: {head}", (20, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        return frame, status, data

    except Exception as e:
        print("[PROCTOR ERROR]", e)
        return frame, "Error", {}