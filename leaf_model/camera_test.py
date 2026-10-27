import cv2
import time

cap = cv2.VideoCapture("/dev/video2", cv2.CAP_V4L2)

if not cap.isOpened():
    print("ERROR: Camera could not be opened")
    exit()

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

time.sleep(1)

cv2.namedWindow("Camera", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Camera", 960, 720)

print("Camera started.")
print("Press Q to quit.")

while True:

    ret, frame = cap.read()

    if not ret:
        print("Frame read failed")
        continue

    # Force a normal 640x480 BGR image
    if len(frame.shape) != 3:
        print("Unexpected frame:", frame.shape)
        continue

    cv2.imshow("Camera", frame)

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
