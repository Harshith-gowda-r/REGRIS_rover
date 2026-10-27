import cv2
import time
from inverse_kinematics import inverse_kinematics


# CAMERA CALIBRATION


FX = 933.98727168
FY = 968.37797809
CX = 349.17260579
CY = 346.05759238

# Camera is 55 mm ABOVE nozzle
CAMERA_TO_NOZZLE_Z = 55.0

CAMERA_DEVICE = "/dev/video2"


# OPEN CAMERA


cap = cv2.VideoCapture(CAMERA_DEVICE, cv2.CAP_V4L2)

if not cap.isOpened():
    print("ERROR: Could not open camera")
    exit()

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

time.sleep(1)

print()

print(" CAMERA -> XYZ -> IK TEST")
print()
print("Click the target.")
print("The terminal will ask for HC-SR04 distance.")
print("Press Q to quit.")
print()

selected_pixel = None


def mouse_callback(event, x, y, flags, param):
    global selected_pixel

    if event == cv2.EVENT_LBUTTONDOWN:
        selected_pixel = (x, y)


# Same window setup as the working camera test
cv2.namedWindow("Camera", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Camera", 960, 720)
cv2.setMouseCallback("Camera", mouse_callback)


while True:

    ret, frame = cap.read()

    if not ret:
        print("Frame read failed")
        continue

    display = frame.copy()

    # IMAGE CENTER


    cv2.line(
        display,
        (305, 240),
        (335, 240),
        (0, 0, 255),
        2
    )

    cv2.line(
        display,
        (320, 225),
        (320, 255),
        (0, 0, 255),
        2
    )


    # SELECTED TARGET


    if selected_pixel is not None:

        u, v = selected_pixel

        cv2.circle(
            display,
            (u, v),
            7,
            (0, 255, 255),
            -1
        )

        cv2.putText(
            display,
            f"({u},{v})",
            (u + 10, v - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 255),
            2
        )

    cv2.imshow("Camera", display)

    key = cv2.waitKey(1) & 0xFF


    # QUIT


    if key == ord("q"):
        break


    # PROCESS CLICK


    if selected_pixel is not None:

        u, v = selected_pixel

        print()
        print(f"Selected pixel: ({u}, {v})")

        try:

            distance = float(
                input("Enter HC-SR04 distance in mm: ")
            )

        except ValueError:

            print("Invalid distance.")
            selected_pixel = None
            continue


        # CAMERA -> 3D


        z_cam = distance

        x_cam = (u - CX) * z_cam / FX
        y_cam = (v - CY) * z_cam / FY


        # CAMERA -> ROVER COORDINATES
        #
        # +X = forward
        # +Y = left
        # +Z = up


        X = z_cam
        Y = -x_cam
        Z = CAMERA_TO_NOZZLE_Z - y_cam

        print()

        print("3D TARGET")

        print(f"Pixel    : ({u}, {v})")
        print(f"Distance : {distance:.1f} mm")

        print()
        print("Camera coordinates:")
        print(f"Xcam = {x_cam:.2f} mm")
        print(f"Ycam = {y_cam:.2f} mm")
        print(f"Zcam = {z_cam:.2f} mm")

        print()
        print("Rover coordinates:")
        print(f"X = {X:.2f} mm")
        print(f"Y = {Y:.2f} mm")
        print(f"Z = {Z:.2f} mm")


        # XYZ -> IK


        print()
        print("Calculating IK...")

        try:

            base, shoulder, elbow = inverse_kinematics(
                X,
                Y,
                Z
            )

            print()

            print("VALID SERVO TARGET")


            print(f"Base     = {base:.2f}°")
            print(f"Shoulder = {shoulder:.2f}°")
            print(f"Elbow    = {elbow:.2f}°")

            print()
            print("ARM WILL NOT MOVE.")
            print("Calculation-only test.")

        except ValueError as e:

            print()

            print("TARGET NOT REACHABLE")


            print(str(e))
            print("No servo movement will occur.")

        print()

        selected_pixel = None


cap.release()
cv2.destroyAllWindows()
