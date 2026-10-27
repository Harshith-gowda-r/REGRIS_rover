import cv2

CAMERA = "/dev/video2"

cap = cv2.VideoCapture(CAMERA, cv2.CAP_V4L2)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

if not cap.isOpened():
    print("ERROR: Cannot open camera")
    exit()

print("Camera running.")
print("RED CROSS = image center (320,240)")
print("Press Q to quit.")

while True:

    ret, frame = cap.read()

    if not ret:
        print("Frame read failed.")
        break

    # Thick red cross
    cv2.line(
        frame,
        (320, 0),
        (320, 480),
        (0, 0, 255),
        3
    )

    cv2.line(
        frame,
        (0, 240),
        (640, 240),
        (0, 0, 255),
        3
    )

    # Large yellow center circle
    cv2.circle(
        frame,
        (320, 240),
        10,
        (0, 255, 255),
        -1
    )

    cv2.putText(
        frame,
        "CENTER (320,240)",
        (10, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (255, 255, 255),
        3
    )

    cv2.imshow("Camera View", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
