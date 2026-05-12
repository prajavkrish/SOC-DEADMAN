"""
Enroll your face as an authorized user.
Uses OpenCV built-in face detection - no extra libraries needed.

Usage:
    python enroll_face.py --name yourname

Look at the camera and press SPACE to capture your face photo.
"""

import cv2
import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--name",   required=True, help="Your name, no spaces (e.g. john)")
parser.add_argument("--camera", type=int, default=0)
args = parser.parse_args()

faces_dir = Path("authorized_faces")
faces_dir.mkdir(exist_ok=True)

# Load OpenCV's built-in face detector (included with opencv, no download needed)
face_cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
face_cascade      = cv2.CascadeClassifier(face_cascade_path)

cap = cv2.VideoCapture(args.camera)
if not cap.isOpened():
    print("ERROR: Cannot open camera", args.camera)
    exit(1)

print(f"Enrolling face for: {args.name}")
print("Look directly at the camera. Press SPACE to capture. Press Q to cancel.")

captured = False
while True:
    ret, frame = cap.read()
    if not ret:
        continue

    gray   = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces  = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
    display = frame.copy()

    face_found = len(faces) > 0

    for (x, y, w, h) in faces:
        cv2.rectangle(display, (x, y), (x + w, y + h), (0, 255, 0), 2)

    status = "Face detected - press SPACE" if face_found else "No face detected - move closer"
    color  = (0, 255, 0) if face_found else (0, 0, 255)

    cv2.putText(display, f"Enrolling: {args.name}",
                (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
    cv2.putText(display, status,
                (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1)
    cv2.putText(display, "SPACE = save    Q = cancel",
                (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)

    cv2.imshow("Face Enrollment", display)
    key = cv2.waitKey(1) & 0xFF

    if key == ord(" "):
        if not face_found:
            print("No face detected in frame. Move closer and try again.")
            continue

        # Save the full frame (detection_agent will extract the face region)
        save_path = faces_dir / f"{args.name}.jpg"
        cv2.imwrite(str(save_path), frame)
        print(f"Saved: {save_path}")
        print("Restart the detection agent to load your enrolled face.")
        captured = True
        break

    elif key == ord("q"):
        print("Cancelled.")
        break

cap.release()
cv2.destroyAllWindows()

if not captured:
    print("No face was enrolled.")