"""
Camera test - run this first to confirm your webcam works.
Press Q to exit the video window.
"""

import cv2
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--camera", type=int, default=0)
args = parser.parse_args()

cap = cv2.VideoCapture(args.camera)

if not cap.isOpened():
    print("ERROR: Cannot open camera", args.camera)
    print("Try:  python test_camera.py --camera 1")
    exit(1)

print("Camera", args.camera, "is working. Press Q to close.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("ERROR: Could not read frame")
        break

    cv2.putText(frame, "Camera OK - Press Q to close",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    cv2.imshow("Camera Test", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
print("Camera test done.")