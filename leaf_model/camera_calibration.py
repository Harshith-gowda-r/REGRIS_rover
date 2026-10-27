import cv2
import numpy as np
import os

CAMERA = "/dev/video2"

# Number of INNER corners
CHECKERBOARD = (9, 6)

# Change this to your actual checkerboard square size in mm
SQUARE_SIZE = 20.0

SAVE_DIR = "calibration_images"
os.makedirs(SAVE_DIR, exist_ok=True)

cap = cv2.VideoCapture(CAMERA)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

print("Camera calibration capture")
print("Press SPACE to save a checkerboard image.")
print("Press Q to quit.")
print("Capture about 15-20 images from different angles.")

count = 0

while True:

    ret, frame = cap.read()

    if not ret:
        print("Camera read failed.")
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    found, corners = cv2.findChessboardCorners(
        gray,
        CHECKERBOARD,
        None
    )

    display = frame.copy()

    if found:
        cv2.drawChessboardCorners(
            display,
            CHECKERBOARD,
            corners,
            found
        )

        cv2.putText(
            display,
            "CHECKERBOARD FOUND - press SPACE",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )
    else:
        cv2.putText(
            display,
            "Move checkerboard until corners are found",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 0, 255),
            2
        )

    cv2.imshow("Camera Calibration", display)

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break

    if key == 32 and found:

        filename = os.path.join(
            SAVE_DIR,
            f"calibration_{count:02d}.jpg"
        )

        cv2.imwrite(filename, frame)

        print("Saved:", filename)

        count += 1

cap.release()
cv2.destroyAllWindows()

print(f"\nCaptured {count} calibration images.")
