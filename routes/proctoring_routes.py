import cv2
from flask import Blueprint, Response
from services.proctoring.proctoring_system import analyze_frame
import services.proctoring.proctoring_system as ps
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
        if camera is None or not camera.isOpened():
            camera = cv2.VideoCapture(0)
    return camera


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
        return

    stop_event.clear()

    while not stop_event.is_set():
        success, frame = cam.read()
        if not success:
            break

        try:
            processed_frame, current_status, head_pos = analyze_frame(frame)

            state.update(current_status)
            state.record_position(head_pos)

            # Sync for app.py
            ps.head_status = head_pos
            ps.head_warnings = state.position_change_count

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

    # 🔥 When loop exits → release camera
    release_camera()


# ================= ROUTES =================
@proctoring_bp.route("/api/proctoring_status")
def get_proctoring_status():
    return state.get_status()


@proctoring_bp.route("/api/proctoring_reset")
def reset_proctoring():
    state.reset()
    return {"message": "State reset"}


@proctoring_bp.route("/api/proctoring_stop")
def stop_proctoring():
    # 🔥 SIGNAL LOOP TO STOP
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