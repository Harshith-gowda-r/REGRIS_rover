import cv2
import numpy as np



# PATH DETECTION SETTINGS


WIDTH = 640
HEIGHT = 480

ROI_START = 0.45

MIN_PATH_AREA = 2000

LEFT_THRESHOLD = 40
SHARP_LEFT_THRESHOLD = 150

RIGHT_THRESHOLD = 40
SHARP_RIGHT_THRESHOLD = 150



# PATH DETECTION


def process_path_frame(frame):


    # Resize


    frame = cv2.resize(
        frame,
        (WIDTH, HEIGHT)
    )

    height, width = frame.shape[:2]

    camera_center = width // 2


    # ROI


    roi_start = int(height * ROI_START)

    roi = frame[
        roi_start:height,
        :
    ]


    # Convert to HSV


    hsv = cv2.cvtColor(
        roi,
        cv2.COLOR_BGR2HSV
    )


    # Detect light / white path


    lower = np.array(
        [0, 0, 70]
    )

    upper = np.array(
        [180, 110, 255]
    )

    mask = cv2.inRange(
        hsv,
        lower,
        upper
    )


    # Clean mask


    kernel = np.ones(
        (5, 5),
        np.uint8
    )

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_OPEN,
        kernel
    )

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_CLOSE,
        kernel
    )


    # Find contours


    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )


    # Default values


    direction = "PATH LOST"

    error = 0

    path_found = False

    path_center = camera_center


    # PATH ANALYSIS


    if contours:

        largest = max(
            contours,
            key=cv2.contourArea
        )

        area = cv2.contourArea(
            largest
        )


        # Check minimum area


        if area > MIN_PATH_AREA:

            M = cv2.moments(
                largest
            )

            if M["m00"] != 0:

                path_center = int(
                    M["m10"] / M["m00"]
                )

                error = (
                    path_center
                    - camera_center
                )

                path_found = True


                # COMMAND GENERATION


                if error < -SHARP_LEFT_THRESHOLD:

                    direction = "SHARP LEFT"

                elif error < -LEFT_THRESHOLD:

                    direction = "LEFT"

                elif error > SHARP_RIGHT_THRESHOLD:

                    direction = "SHARP RIGHT"

                elif error > RIGHT_THRESHOLD:

                    direction = "RIGHT"

                else:

                    direction = "FORWARD"


                # Print command


                print(
                    f"Error: {error:4d}  ->  "
                    f"COMMAND: {direction}",
                    flush=True
                )


                # Draw path center


                cv2.circle(
                    frame,
                    (
                        path_center,
                        roi_start + 80
                    ),
                    10,
                    (255, 0, 255),
                    -1
                )


                # Draw contour


                contour_display = (
                    largest
                    + np.array(
                        [0, roi_start]
                    )
                )

                cv2.drawContours(
                    frame,
                    [contour_display],
                    -1,
                    (0, 255, 0),
                    2
                )


    # PATH LOST


    if not path_found:

        direction = "PATH LOST"

        error = 0

        print(
            "Error: ----  ->  COMMAND: PATH LOST",
            flush=True
        )


    # CAMERA CENTER


    cv2.line(
        frame,
        (camera_center, 0),
        (camera_center, height),
        (0, 0, 255),
        2
    )


    # ROI LINE


    cv2.line(
        frame,
        (0, roi_start),
        (width, roi_start),
        (255, 0, 255),
        2
    )


    # COMMAND DISPLAY


    cv2.putText(
        frame,
        f"COMMAND: {direction}",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (0, 255, 255),
        2
    )


    # ERROR DISPLAY


    cv2.putText(
        frame,
        f"Error: {error}",
        (20, 80),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        (255, 255, 255),
        2
    )


    # STATUS DISPLAY


    if path_found:

        status = "PATH DETECTED"
        status_color = (0, 255, 0)

    else:

        status = "PATH LOST"
        status_color = (0, 0, 255)

    cv2.putText(
        frame,
        status,
        (20, 115),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.65,
        status_color,
        2
    )


    # TITLE


    cv2.putText(
        frame,
        "CAMERA PATH COMMAND",
        (20, 150),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.55,
        (255, 255, 255),
        2
    )


    # RETURN ALL DATA


    return (
        frame,
        direction,
        error,
        path_found
    )
