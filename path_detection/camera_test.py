import cv2
from path_detect import process_path_frame

CAMERA = "/dev/video4"

cap = cv2.VideoCapture(CAMERA, cv2.CAP_V4L2)

if not cap.isOpened():
    print(f"ERROR: Could not open camera {CAMERA}")
    exit()

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)


print("REGRIS PATH DETECTION")
print("Camera:", CAMERA)
print("Stream: PATH DETECTION ONLY")
print("Press Q to quit")


while True:

    ret, frame = cap.read()

    if not ret:
        print("ERROR: Could not read frame")
        break

    # Process camera image
    processed, direction, error, path_found = process_path_frame(frame)

    # Show processed image
    cv2.imshow("REGRIS - PATH DETECTION", processed)

    # Press Q to quit
    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()

