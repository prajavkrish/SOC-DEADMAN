"""
Visual SOC Deadman Switch - Detection Agent
===========================================
Uses OpenCV built-in face detection instead of face_recognition/dlib.
No C++ compiler or Visual Studio required.

What it detects:
  - Cell phone near the screen  (YOLOv8)
  - Multiple people             (YOLOv8)
  - User absence                (OpenCV face detection)
  - Unknown face                (OpenCV LBPH face recognizer)
"""

import cv2
import time
import logging
import argparse
import requests
import logging
import os
from logging.handlers import RotatingFileHandler
import numpy as np
from datetime import datetime
from pathlib import Path

# Create logs folder
if not os.path.exists("logs"):
    os.makedirs("logs")

# Logger setup
log = logging.getLogger("SOC_AGENT")
log.setLevel(logging.INFO)

# Log format
formatter = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(filename)s:%(lineno)d | %(message)s"
)

# File logging
file_handler = RotatingFileHandler(
    "logs/agent.log",
    maxBytes=5 * 1024 * 1024,
    backupCount=5
)

file_handler.setFormatter(formatter)
# Console logging
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)

# Attach handlers
log.addHandler(file_handler)
log.addHandler(console_handler)
# -------------------------------------------------------
# Optional: YOLOv8 for phone and person detection
# -------------------------------------------------------
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("WARNING: ultralytics not installed. Run setup.bat first.")

# -------------------------------------------------------
# Settings
# -------------------------------------------------------
DEFAULT_API_URL             = "http://localhost:5000/api"
SCREENSHOT_DIR              = Path("forensic_screenshots")
AUTHORIZED_FACES_DIR        = Path("authorized_faces")

PHONE_CONFIDENCE_THRESHOLD  = 0.45
PERSON_CONFIDENCE_THRESHOLD = 0.50
ABSENCE_TIMEOUT_SECONDS     = 10.0
HEARTBEAT_INTERVAL_SECONDS  = 5.0
ALERT_COOLDOWN_SECONDS      = 30.0

# Face recognizer: lower = stricter match. 80 is a good starting value.
LBPH_CONFIDENCE_THRESHOLD   = 80.0

COCO_PHONE_CLASS            = 67
COCO_PERSON_CLASS           = 0

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("soc-agent")


# -------------------------------------------------------
# Dashboard API
# -------------------------------------------------------
class DashboardClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.session  = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    def post_event(self, event_type, severity, message,
                   details=None, confidence=None, screenshot_path=None):
        payload = {"type": event_type, "severity": severity, "message": message}
        if details:         payload["details"]        = details
        if confidence:      payload["confidence"]     = round(confidence, 3)
        if screenshot_path: payload["screenshotPath"] = screenshot_path
        try:
            r = self.session.post(f"{self.base_url}/events", json=payload, timeout=5)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            log.error(f"Could not post event: {e}")
            return {}

    def post_status(self, is_running, face_detected=None,
                    phone_detected=None, multi_person=None,
                    fps=None, active_threats=0):
        payload = {"isRunning": is_running, "activeThreats": active_threats}
        if face_detected  is not None: payload["faceDetected"]        = face_detected
        if phone_detected is not None: payload["phoneDetected"]       = phone_detected
        if multi_person   is not None: payload["multiPersonDetected"] = multi_person
        if fps            is not None: payload["fps"]                 = round(fps, 1)
        try:
            self.session.post(f"{self.base_url}/status", json=payload, timeout=5)
        except Exception as e:
            log.warning(f"Heartbeat failed: {e}")

    def save_screenshot_record(self, filename, path, event_id=None, label=None):
        payload = {"filename": filename, "path": path}
        if event_id: payload["eventId"] = event_id
        if label:    payload["label"]   = label
        try:
            self.session.post(f"{self.base_url}/screenshots", json=payload, timeout=5)
        except Exception as e:
            log.warning(f"Could not save screenshot record: {e}")


# -------------------------------------------------------
# OpenCV face detector (Haar Cascade - built into opencv)
# -------------------------------------------------------
def load_face_cascade():
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    cascade      = cv2.CascadeClassifier(cascade_path)
    if cascade.empty():
        log.error("Failed to load face cascade. Check OpenCV installation.")
    else:
        log.info("OpenCV face detector loaded.")
    return cascade


# -------------------------------------------------------
# LBPH Face Recognizer - trains on photos in authorized_faces/
# Returns: (recognizer, trained=True/False)
# -------------------------------------------------------
def load_face_recognizer(faces_dir: Path, cascade):
    faces_dir.mkdir(exist_ok=True)
    images = []
    labels = []

    for img_path in faces_dir.glob("*.[jp][pn][g]*"):
        img  = cv2.imread(str(img_path))
        if img is None:
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Detect face in the enrolled photo
        rects = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
        if len(rects) == 0:
            log.warning(f"No face found in enrolled photo: {img_path.name}")
            continue
        x, y, w, h = rects[0]
        face_roi   = cv2.resize(gray[y:y+h, x:x+w], (100, 100))
        images.append(face_roi)
        labels.append(0)   # All enrolled faces get label 0 = "authorized"
        log.info(f"Enrolled face loaded: {img_path.name}")

    recognizer = cv2.face.LBPHFaceRecognizer_create()

    if images:
        recognizer.train(images, np.array(labels))
        log.info(f"Face recognizer trained on {len(images)} authorized face(s).")
        return recognizer, True
    else:
        log.info("No enrolled faces found in authorized_faces/ — any face = authorized user.")
        return recognizer, False


# -------------------------------------------------------
# Screenshot helper
# -------------------------------------------------------
def save_screenshot(frame: np.ndarray, label: str) -> str:
    SCREENSHOT_DIR.mkdir(exist_ok=True)
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{label}_{ts}.jpg"
    filepath = SCREENSHOT_DIR / filename
    cv2.imwrite(str(filepath), frame)
    log.info(f"Screenshot saved: {filepath}")
    return str(filepath)


# -------------------------------------------------------
# Main detection loop
# -------------------------------------------------------
def run(api_url: str, camera_index: int):
    client       = DashboardClient(api_url)
    face_cascade = load_face_cascade()

    client.post_status(is_running=True, active_threats=0)
    log.info(f"Agent started. Reporting to: {api_url}")

    # Load face recognizer
    recognizer, face_recognition_trained = load_face_recognizer(AUTHORIZED_FACES_DIR, face_cascade)

    # Load YOLOv8 (downloads yolov8n.pt ~6MB on first run)
    yolo_model = None
    if YOLO_AVAILABLE:
        log.info("Loading YOLOv8 model (downloads ~6MB on first run)...")
        yolo_model = YOLO("yolov8n.pt")
        log.info("YOLOv8 ready.")

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        log.error(f"Cannot open camera {camera_index}. Try --camera 1")
        client.post_status(is_running=False)
        return

    log.info(f"Webcam {camera_index} open. Press Q in the video window to quit.")

    # State
    last_face_seen   = time.time()
    last_alert_times = {}
    frame_count      = 0
    fps_timer        = time.time()
    current_fps      = 0.0
    last_heartbeat   = 0.0
    active_threats   = 0

    def can_alert(alert_type: str) -> bool:
        now  = time.time()
        last = last_alert_times.get(alert_type, 0)
        if now - last >= ALERT_COOLDOWN_SECONDS:
            last_alert_times[alert_type] = now
            return True
        return False

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                log.warning("Frame read failed — retrying...")
                time.sleep(0.1)
                continue

            frame_count += 1
            now          = time.time()

            if now - fps_timer >= 2.0:
                current_fps = frame_count / (now - fps_timer)
                frame_count = 0
                fps_timer   = now

            display        = frame.copy()
            phone_detected = False
            face_detected  = False
            person_count   = 0
            active_threats = 0

            # ---------------------------------------------------
            # YOLO: phones and people
            # ---------------------------------------------------
            if yolo_model is not None:
                results = yolo_model(frame, verbose=False)[0]
                for box in results.boxes:
                    cls_id          = int(box.cls[0])
                    conf            = float(box.conf[0])
                    x1, y1, x2, y2 = map(int, box.xyxy[0])

                    if cls_id == COCO_PERSON_CLASS and conf >= PERSON_CONFIDENCE_THRESHOLD:
                        person_count += 1
                        cv2.rectangle(display, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.putText(display, f"Person {conf:.0%}",
                                    (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

                    elif cls_id == COCO_PHONE_CLASS and conf >= PHONE_CONFIDENCE_THRESHOLD:
                        phone_detected  = True
                        active_threats += 1
                        cv2.rectangle(display, (x1, y1), (x2, y2), (0, 0, 255), 2)
                        cv2.putText(display, f"PHONE {conf:.0%}",
                                    (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

                        if can_alert("phone_detected"):
                            log.warning(f"ALERT: PHONE DETECTED (conf={conf:.0%})")
                            ss = save_screenshot(frame, "phone_detected")
                            ev = client.post_event(
                                event_type="phone_detected",
                                severity="critical",
                                message="Cell phone detected near workstation screen",
                                details=f"YOLOv8 confidence {conf:.1%}. Possible visual data exfiltration.",
                                confidence=conf,
                                screenshot_path=ss,
                            )
                            if ev.get("id"):
                                client.save_screenshot_record(
                                    Path(ss).name, ss,
                                    event_id=ev["id"],
                                    label="Phone Detection Evidence"
                                )

                if person_count > 1:
                    active_threats += 1
                    if can_alert("multi_person"):
                        log.warning(f"ALERT: {person_count} people at workstation")
                        ss = save_screenshot(frame, "multi_person")
                        ev = client.post_event(
                            event_type="multi_person",
                            severity="high",
                            message=f"Multiple persons detected at workstation ({person_count})",
                            details="Possible shoulder-surfing or unauthorized presence.",
                            confidence=0.9,
                            screenshot_path=ss,
                        )
                        if ev.get("id"):
                            client.save_screenshot_record(
                                Path(ss).name, ss,
                                event_id=ev["id"],
                                label="Multi-Person Detection Evidence"
                            )

            # ---------------------------------------------------
            # OpenCV face detection + LBPH recognition
            # ---------------------------------------------------
            gray       = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray_eq    = cv2.equalizeHist(gray)   # improves detection in variable lighting
            face_rects = face_cascade.detectMultiScale(
                gray_eq, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
            )

            for (fx, fy, fw, fh) in face_rects:
                face_roi = cv2.resize(gray_eq[fy:fy+fh, fx:fx+fw], (100, 100))

                is_authorized = False

                if face_recognition_trained:
                    # Predict: label 0 = authorized. Higher confidence value = worse match in LBPH.
                    label, confidence_val = recognizer.predict(face_roi)
                    is_authorized = (label == 0 and confidence_val < LBPH_CONFIDENCE_THRESHOLD)
                else:
                    # No enrolled faces — treat any face as authorized
                    is_authorized = True

                color = (0, 255, 0) if is_authorized else (0, 140, 255)
                tag   = "AUTHORIZED" if is_authorized else "UNKNOWN"

                cv2.rectangle(display, (fx, fy), (fx + fw, fy + fh), color, 2)
                cv2.putText(display, tag,
                            (fx, fy - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1)

                if is_authorized:
                    face_detected  = True
                    last_face_seen = now

                elif face_recognition_trained and can_alert("unauthorized_access"):
                    log.warning("ALERT: UNKNOWN FACE at workstation")
                    ss = save_screenshot(frame, "unknown_face")
                    client.post_event(
                        event_type="unauthorized_access",
                        severity="critical",
                        message="Unrecognized face detected at SOC workstation",
                        details="Face does not match any enrolled authorized user.",
                        screenshot_path=ss,
                    )

            # ---------------------------------------------------
            # User absence
            # ---------------------------------------------------
            absence = now - last_face_seen
            if absence >= ABSENCE_TIMEOUT_SECONDS and can_alert("user_absent"):
                log.warning(f"ALERT: USER ABSENT for {absence:.0f}s")
                ss = save_screenshot(frame, "user_absent")
                client.post_event(
                    event_type="user_absent",
                    severity="high",
                    message=f"Authorized user absent for {absence:.0f} seconds",
                    details="Unattended SOC workstation — screen may contain sensitive data.",
                    screenshot_path=ss,
                )
                active_threats += 1

            # ---------------------------------------------------
            # HUD overlay
            # ---------------------------------------------------
            hud_color = (0, 0, 255) if active_threats else (0, 200, 0)
            hud_text  = f"THREATS: {active_threats}" if active_threats else "ALL CLEAR"

            cv2.putText(display, hud_text,
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, hud_color, 2)
            cv2.putText(display, f"FPS: {current_fps:.1f}",
                        (10, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)
            cv2.putText(display, f"Persons: {person_count}",
                        (10, 78), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)
            cv2.putText(display, f"Faces detected: {len(face_rects)}",
                        (10, 98), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)

            if absence >= 5:
                cv2.putText(display, f"Absent: {absence:.0f}s",
                            (10, 118), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 140, 255), 1)

            cv2.imshow("Visual SOC Deadman Switch", display)

            # ---------------------------------------------------
            # Heartbeat
            # ---------------------------------------------------
            if now - last_heartbeat >= HEARTBEAT_INTERVAL_SECONDS:
                client.post_status(
                    is_running=True,
                    face_detected=face_detected,
                    phone_detected=phone_detected,
                    multi_person=person_count > 1,
                    fps=current_fps,
                    active_threats=active_threats,
                )
                last_heartbeat = now

            if cv2.waitKey(1) & 0xFF == ord("q"):
                log.info("Quit by user.")
                break

    except KeyboardInterrupt:
        log.info("Stopped.")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        client.post_status(is_running=False, active_threats=0)
        log.info("Agent offline. Dashboard notified.")


# -------------------------------------------------------
# Entry point
# -------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visual SOC Deadman Switch — Detection Agent")
    parser.add_argument("--api-url", default=DEFAULT_API_URL,
                        help="Dashboard API URL (e.g. https://your-app.replit.app/api)")
    parser.add_argument("--camera", type=int, default=0,
                        help="Camera index (0 = built-in, 1 = external)")
    args = parser.parse_args()
    run(api_url=args.api_url, camera_index=args.camera)