import cv2
import os
import time

CAMERA = "/dev/video2"

CHECKERBOARD = (9, 6)
SQUARE_SIZE = 6.4  # mm

SAVE_DIR = "calibration_images"
os.makedirs(SAVE_DIR, exist_ok=True)

cap = cv2.VideoCapture(CAMERA, cv2.CAP_V4L2)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

if not cap.isOpened():
    print("ERROR: Cannot open camera")
    exit()

print("=" * 55)
print("CAMERA CALIBRATION IMAGE CAPTURE")
print("=" * 55)
print("Resolution: 640 x 480")
print("Checkerboard: 9 x 6 inner corners")
print("Square size: 6.4 mm")
print()
print("Place the checkerboard on the phone screen.")
print("Move it around the camera view and change its angle.")
print()
print("Press ENTER to capture an image.")
print("Press Q then ENTER to quit.")
print("=" * 55)

count = 0

while True:

    ret, frame = cap.read()

    if not ret:
        print("Camera frame failed.")
        break

    # Detect checkerboard
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    found, corners = cv2.findChessboardCorners(
        gray,
        CHECKERBOARD,
        None
    )

    if found:
        print(
            f"\rCheckerboard detected | "
            f"Images captured: {count}",
            end="",
            flush=True
        )
    else:
        print(
            f"\rCheckerboard NOT detected | "
            f"Images captured: {count}",
            end="",
            flush=True
        )

    # Wait for keyboard input without OpenCV GUI
    command = input("\nCommand [ENTER=capture, q=quit]: ").strip().lower()

    if command == "q":
        break

    if command == "" and found:

        filename = os.path.join(
            SAVE_DIR,
            f"calibration_{count:02d}.jpg"
        )

        cv2.imwrite(filename, frame)

        print("Saved:", filename)

        count += 1

        time.sleep(0.3)

    elif command == "":
        print("Checkerboard not detected. Move it and try again.")

cap.release()

print()
print("=" * 55)
print(f"CAPTURE COMPLETE: {count} images")
print("=" * 55)
