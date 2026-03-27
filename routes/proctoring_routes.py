import cv2
from flask import Blueprint, Response, jsonify
from services.proctoring.proctoring_system import (
    analyze_frame,
    SuspicionTracker,
    MovementTracker
)
import threading
import atexit

proctoring_bp = Blueprint("proctoring_bp", __name__)

camera = None
camera_lock = threading.Lock()
stop_event = threading.Event()


# ================= CAMERA =================
def get_camera():
    global camera
    with camera_lock:
        if camera is not None and camera.isOpened():
            return camera

        for i in range(3):
            try:
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    ret, _ = cap.read()
                    if ret:
                        print(f"[CAMERA] Using camera index {i}")
                        camera = cap
                        return camera
                    cap.release()
            except Exception as e:
                print(f"[CAMERA] Index {i} failed: {e}")

        print("[CAMERA ERROR] No working camera found")
        camera = None
    return None


def release_camera():
    global camera
    with camera_lock:
        if camera and camera.isOpened():
            try:
                camera.release()
            except:
                pass
        camera = None


# ================= STATE =================
class ProctoringState:
    def __init__(self):
        self.status = "Normal"
        self.warning_count = 0
        self.position_change_count = 0
        self._last_position = None
        self._lock = threading.Lock()

    def update(self, status):
        with self._lock:
            self.status = status
            if status != "Normal":
                self.warning_count += 1

    def record_position(self, position):
        if position == "Unknown":
            return
        with self._lock:
            if self._last_position and position != self._last_position:
                self.position_change_count += 1
            self._last_position = position

    def get_status(self):
        with self._lock:
            return {
                "status": self.status,
                "warning_count": self.warning_count,
                "position_changes": self.position_change_count
            }

    def reset(self):
        with self._lock:
            self.status = "Normal"
            self.warning_count = 0
            self.position_change_count = 0
            self._last_position = None


state = ProctoringState()


# ================= STREAM =================
def generate_frames():
    cam = get_camera()

    if not cam or not cam.isOpened():
        print("[CAMERA ERROR] Cannot start stream — no camera available")
        return

    stop_event.clear()

    # ✅ IMPORTANT: create once (NOT inside loop)
    tracker = SuspicionTracker()
    movement = MovementTracker()

    while not stop_event.is_set():
        ret, frame = cam.read()
        if not ret:
            print("[CAMERA ERROR] Frame not received")
            continue

        try:
            # ✅ NEW: pass tracker + movement
            processed_frame, current_status, data = analyze_frame(
                frame, tracker, movement
            )

            # update global state
            state.update(current_status)

            # optional: track head movement (if available)
            head_pos = data.get("status", "Unknown")
            state.record_position(head_pos)

        except Exception as e:
            print("[Proctoring Error]", e)
            processed_frame = frame

        ret, buffer = cv2.imencode('.jpg', processed_frame)
        if not ret:
            continue

        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' +
            buffer.tobytes() + b'\r\n'
        )

    release_camera()


# ================= ROUTES =================
@proctoring_bp.route("/api/head_status")
def get_head_status():
    return jsonify(state.get_status())


@proctoring_bp.route("/api/proctoring_reset")
def reset_proctoring():
    state.reset()
    return {"message": "State reset"}


@proctoring_bp.route("/api/proctoring_stop", methods=["GET", "POST"])
def stop_proctoring():
    stop_event.set()
    release_camera()
    state.reset()
    return {"message": "Proctoring stopped safely"}


@proctoring_bp.route("/video_feed")
def video_feed():
    state.reset()
    stop_event.clear()

    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


# ================= CLEANUP =================
def cleanup():
    stop_event.set()
    release_camera()


atexit.register(cleanup)