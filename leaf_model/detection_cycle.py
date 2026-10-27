import cv2
import time
import serial
import os
import json

from ultralytics import YOLO
from llm_analyzer import analyze_with_llm, parse_decision



# CONFIGURATION

MODEL_PATH = os.getenv(
    "MODEL_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "best.pt")
)

CAMERA_SOURCE = 2

OBSERVATION_TIME = 2.0
MAX_FRAMES = 6

CONFIDENCE = 0.5

CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

ARDUINO_PORT = "/dev/ttyUSB0"
ARDUINO_BAUDRATE = 115200

# Final 2 frames actually sent to detection LLM
FRAMES_TO_SAVE = 2



# ARDUINO / PUMP CONTROL


def spray_with_arduino(duration):

    duration = max(7, min(15, int(duration)))

    print(f"\nSending spray command to Arduino: {duration} seconds")

    arduino = None

    try:
        arduino = serial.Serial(
            ARDUINO_PORT,
            ARDUINO_BAUDRATE,
            timeout=2
        )

        # Arduino resets when serial connection opens.
        time.sleep(2)

        command = f"SPRAY {duration}\n"
        arduino.write(command.encode())

        print("Arduino command sent.")

        while True:

            response = arduino.readline().decode(
                errors="ignore"
            ).strip()

            if response:
                print("Arduino:", response)

            if response == "PUMP_OFF":

                print("Spraying completed.")

                break

    finally:

        if arduino is not None and arduino.is_open:
            arduino.close()



# SAVE FINAL LLM FRAMES


def save_final_frames(frames, output_directory):

    os.makedirs(output_directory, exist_ok=True)

    saved_paths = []

    frames_to_save = frames[-FRAMES_TO_SAVE:]

    for i, frame in enumerate(frames_to_save, start=1):

        path = os.path.join(
            output_directory,
            f"frame_{i}.jpg"
        )

        success = cv2.imwrite(path, frame)

        if success:
            saved_paths.append(path)

    return saved_paths



# MAIN DETECTION CYCLE


def run_detection_cycle(
    plant_id="plant_001",
    view_id="view_001"
):

    print("Loading YOLO model...")

    model = YOLO(MODEL_PATH)

    print("Opening camera...")

    cap = cv2.VideoCapture(
        CAMERA_SOURCE,
        cv2.CAP_V4L2
    )

    if not cap.isOpened():

        raise RuntimeError(
            "Could not open Zebronics camera"
        )

    cap.set(
        cv2.CAP_PROP_FRAME_WIDTH,
        CAMERA_WIDTH
    )

    cap.set(
        cv2.CAP_PROP_FRAME_HEIGHT,
        CAMERA_HEIGHT
    )


    # START LIVE FEED


    print("Starting live camera feed...")

    while True:

        ret, frame = cap.read()

        if not ret:
            continue

        cv2.imshow(
            "Leaf Disease Detection",
            frame
        )

        key = cv2.waitKey(1) & 0xFF

        if key == 27:

            cap.release()
            cv2.destroyAllWindows()

            return None

        break

    print("Live feed ready.")


    # 2-SECOND COUNTDOWN


    print("Starting 2-second countdown...")

    countdown_start = time.monotonic()

    while True:

        ret, frame = cap.read()

        if not ret:
            continue

        elapsed = (
            time.monotonic()
            - countdown_start
        )

        remaining = 2.0 - elapsed

        if remaining <= 0:
            break

        display_frame = frame.copy()

        number = int(remaining) + 1

        cv2.putText(
            display_frame,
            f"Observation starts in {number}",
            (30, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 255),
            2
        )

        cv2.imshow(
            "Leaf Disease Detection",
            display_frame
        )

        if cv2.waitKey(1) & 0xFF == 27:

            cap.release()
            cv2.destroyAllWindows()

            return None


    # START YOLO OBSERVATION


    print("OBSERVATION STARTED")

    observation_start = time.monotonic()

    detections_log = []

    captured_frames = []


    # 2-SECOND YOLO LOOP


    while True:

        elapsed = (
            time.monotonic()
            - observation_start
        )

        if elapsed >= OBSERVATION_TIME:
            break

        ret, frame = cap.read()

        if not ret:
            continue


        # YOLO inference


        results = model.predict(
            frame,
            imgsz=416,
            conf=CONFIDENCE,
            verbose=False
        )

        result = results[0]


        # Annotated frame


        annotated_frame = result.plot()


        # Detection information


        frame_detections = []

        if result.boxes is not None:

            for box in result.boxes:

                class_id = int(
                    box.cls[0]
                )

                confidence = float(
                    box.conf[0]
                )

                class_name = result.names[
                    class_id
                ]

                x1, y1, x2, y2 = (
                    box.xyxy[0].tolist()
                )

                frame_detections.append(
                    {
                        "class": class_name,
                        "confidence": round(
                            confidence,
                            4
                        ),
                        "bbox": [
                            round(x1, 1),
                            round(y1, 1),
                            round(x2, 1),
                            round(y2, 1)
                        ]
                    }
                )

        detections_log.append(
            {
                "time": round(
                    time.monotonic()
                    - observation_start,
                    3
                ),
                "detections": frame_detections
            }
        )


        # Keep last 6 frames


        captured_frames.append(
            frame.copy()
        )

        if len(captured_frames) > MAX_FRAMES:

            captured_frames.pop(0)


        # Display


        cv2.imshow(
            "Leaf Disease Detection",
            annotated_frame
        )

        if cv2.waitKey(1) & 0xFF == 27:
            break


    # CAMERA CLEANUP


    cap.release()

    cv2.destroyAllWindows()


    # DETECTION SUMMARY


    print("\n--- DETECTION COMPLETE ---")

    print(
        f"YOLO frames analysed: "
        f"{len(detections_log)}"
    )

    print(
        f"Last frames captured for LLM: "
        f"{len(captured_frames)}"
    )


    # SAVE FINAL 2 FRAMES


    frame_directory = os.path.join(
        os.path.expanduser("~/leaf_model"),
        "detection_frames",
        plant_id,
        view_id
    )

    saved_frame_paths = save_final_frames(
        captured_frames,
        frame_directory
    )

    print(
        f"Saved final {len(saved_frame_paths)} "
        f"LLM frames."
    )

    for path in saved_frame_paths:
        print("  ", path)


    # SEND DATA TO LLM


    print(
        "\nSending YOLO data + last 6 frames "
        "to OpenRouter..."
    )

    llm_response = analyze_with_llm(
        captured_frames,
        detections_log
    )


    # PARSE DECISION


    decision = parse_decision(
        llm_response
    )


    # SAVE DISEASE SUMMARY


    summary_path = os.path.join(
        frame_directory,
        "summary.txt"
    )

    with open(summary_path, "w") as summary_file:

        summary_file.write(
            "Detection Cycle Summary\n"
        )

        summary_file.write(
            "=======================\n\n"
        )

        summary_file.write(
            f"Disease: "
            f"{decision['disease_name']}\n"
        )

        summary_file.write(
            f"Intensity: "
            f"{decision['intensity']}\n"
        )

        summary_file.write(
            f"Spray Needed: "
            f"{'YES' if decision['spray_needed'] else 'NO'}\n"
        )

        if decision["spray_needed"]:

            summary_file.write(
                f"Spray Duration: "
                f"{decision['duration']} seconds\n"
            )

        else:

            summary_file.write(
                "Spray Duration: N/A\n"
            )

    print(
        f"Detection summary saved: {summary_path}"
    )


    # FINAL OUTPUT


    print("\n--- FINAL OUTPUT ---")

    print(
        f"disease: {decision['disease_name']}"
    )

    print(
        f"intensity: {decision['intensity']}"
    )

    if decision["spray_needed"]:

        print("spray needed: YES")

        print(
            f"duration: "
            f"{decision['duration']} seconds"
        )

        print(
            "Spraying will be handled by "
            "plant_automation.py."
        )

    else:

        print("spray needed: NO")


    # RETURN COMPLETE RESULT


    return {
        "disease_name": decision["disease_name"],
        "intensity": decision["intensity"],
        "spray_needed": decision["spray_needed"],
        "duration": decision["duration"],
        "saved_frames": saved_frame_paths,
        "detections": detections_log,
        "llm_response": llm_response
    }



# PROGRAM ENTRY POINT


if __name__ == "__main__":

    result = run_detection_cycle()

    if result is not None:

        print("\nDetection cycle result:")

        print(
            json.dumps(
                {
                    "disease_name":
                        result["disease_name"],
                    "intensity":
                        result["intensity"],
                    "spray_needed":
                        result["spray_needed"],
                    "duration":
                        result["duration"],
                    "saved_frames":
                        result["saved_frames"]
                },
                indent=2
            )
        )
