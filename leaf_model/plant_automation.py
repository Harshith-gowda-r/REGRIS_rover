import os
import sys
import time
import serial

from camera_manager import CameraManager
from camera_to_xyz import camera_pixel_to_xyz
from inverse_kinematics import inverse_kinematics_detailed

from position_planner import choose_next_position
from coverage_manager import CoverageManager

from detection_cycle import (
    run_detection_cycle,
    spray_with_arduino
)



# CONFIGURATION


ARDUINO_PORT = "/dev/ttyUSB0"
ARDUINO_BAUDRATE = 115200

CAMERA_DEVICE = "/dev/video2"

PLANT_ID = "plant_001"

# Distance used to reject a position that is too close
# to an already viewed position.
MIN_VIEW_DISTANCE_MM = 30.0

# Distance used to prevent spraying the same physical
# region twice.
MIN_SPRAY_DISTANCE_MM = 30.0

# Maximum distance the numerical IK is allowed to adjust
# the requested XYZ position to a reachable position.
MAX_IK_ADJUSTMENT_MM = 70.0



# ARDUINO CONTROLLER


class ArduinoController:

    def __init__(
        self,
        port=ARDUINO_PORT,
        baudrate=ARDUINO_BAUDRATE
    ):

        self.port = port
        self.baudrate = baudrate
        self.serial = None


    # CONNECT


    def connect(self):

        print(
            f"Connecting to Arduino "
            f"{self.port}..."
        )

        self.serial = serial.Serial(
            self.port,
            self.baudrate,
            timeout=1
        )

        # Arduino resets when serial opens
        time.sleep(2)

        # Clear old serial data
        self.serial.reset_input_buffer()

        print("Arduino connected.")


    # SEND


    def send(self, command):

        if self.serial is None:

            raise RuntimeError(
                "Arduino is not connected."
            )

        command = command.strip()

        print(
            f"Arduino command: {command}"
        )

        self.serial.write(
            (command + "\n").encode()
        )


    # WAIT FOR ARM REACHED


    def wait_for_arm_reached(
        self,
        timeout=30
    ):

        start = time.monotonic()

        while (
            time.monotonic() - start
            < timeout
        ):

            line = (
                self.serial.readline()
                .decode(
                    errors="ignore"
                )
                .strip()
            )

            if not line:
                continue

            print(
                "Arduino:",
                line
            )

            if line == "ARM_REACHED":

                return True

            if line == "STOPPED":

                return False

        raise TimeoutError(
            "Timed out waiting for ARM_REACHED"
        )


    # DISTANCE


    def get_distance(self):

        self.send("DISTANCE")

        start = time.monotonic()

        while (
            time.monotonic() - start
            < 10
        ):

            line = (
                self.serial.readline()
                .decode(
                    errors="ignore"
                )
                .strip()
            )

            if not line:
                continue

            print(
                "Arduino:",
                line
            )

            # Expected Arduino response:
            #
            # DISTANCE 150

            if line.startswith(
                "DISTANCE "
            ):

                value = line.split(
                    " ",
                    1
                )[1]

                return float(value)

        raise TimeoutError(
            "Timed out waiting for DISTANCE"
        )


    # HOME


    def home(self):

        self.send("HOME")

        return self.wait_for_arm_reached()


    # MOVE


    def move(
        self,
        base,
        shoulder,
        elbow
    ):

        # Hard safety limit.
        # Servo range MUST remain 0–90 degrees.

        base = int(round(base))

        shoulder = int(round(shoulder))

        elbow = int(round(elbow))

        command = f"MOVE {base} {shoulder} {elbow}"

        self.send(command)

        return self.wait_for_arm_reached()


    # CLOSE


    def close(self):

        if (
            self.serial is not None
            and
            self.serial.is_open
        ):

            self.serial.close()

            self.serial = None



# ROUNDING / SAFETY SERVO LIMIT


def clamp_servo(value):

    return max(
        0.0,
        min(90.0, float(value))
    )



# CAPTURE POSITION CAMERA FRAME


def get_position_frame(camera):

    return camera.capture_stable_frame(
        discard_frames=5
    )



# MAIN AUTOMATION


def main():

    print()
    print("=" * 60)
    print("        AGRICULTURAL PLANT AUTOMATION")
    print("=" * 60)
    print()


    # Create controllers


    arduino = ArduinoController()

    camera = CameraManager(
        device=CAMERA_DEVICE,
        width=640,
        height=480
    )

    coverage = CoverageManager(
        PLANT_ID
    )

    # Connect Arduino


    arduino.connect()

    try:


        # START AT HOME


        print("\nReturning arm to HOME...")

        arduino.home()

        print(
            "Arm is at HOME."
        )


        # POSITION CAMERA MODE


        print(
            "\nOpening camera for "
            "position planning..."
        )

        camera.open()

        view_number = (
            coverage.view_count + 1
        )


        # MAIN COVERAGE LOOP


        while True:

            print()
            print("=" * 60)

            print(
                f"POSITION PLANNING "
                f"VIEW {view_number}"
            )

            print("=" * 60)


            # Capture current plant view


            frame = get_position_frame(
                camera
            )


            # Ask Position LLM


            history = (
                coverage
                .get_history_for_llm()
            )

            position = (
                choose_next_position(
                    frame,
                    history
                )
            )


            # Coverage complete


            if not position[
                "target_found"
            ]:

                print(
                    "\nVisible plant coverage "
                    "is complete."
                )

                break

            pixel = position[
                "target_pixel"
            ]

            pixel_x = pixel["x"]
            pixel_y = pixel["y"]

            print(
                f"\nSelected target pixel: "
                f"({pixel_x}, {pixel_y})"
            )


            # Ultrasonic distance


            print(
                "\nGetting plant distance..."
            )

            distance_mm = (
                arduino.get_distance()
            )

            print(
                f"Plant distance: "
                f"{distance_mm:.1f} mm"
            )


            # Safety distance


            if distance_mm < 30.0:

                print(
                    "\nPlant is too close "
                    "for safe operation."
                )

                print(
                    "Asking Position LLM "
                    "for another region..."
                )

                continue


            # Camera pixel → XYZ


            xyz_tuple = (
                camera_pixel_to_xyz(
                    pixel_x,
                    pixel_y,
                    distance_mm
                )
            )

            x, y, z = xyz_tuple

            requested_xyz = {
                "x": float(x),
                "y": float(y),
                "z": float(z)
            }

            print(
                "\nTarget XYZ:"
            )

            print(
                f"X = {x:.2f} mm"
            )

            print(
                f"Y = {y:.2f} mm"
            )

            print(
                f"Z = {z:.2f} mm"
            )


            # Check whether already viewed


            if coverage.position_already_viewed(
                requested_xyz,
                MIN_VIEW_DISTANCE_MM
            ):

                print(
                    "\nTarget is too close to "
                    "an already viewed position."
                )

                print(
                    "Asking Position LLM "
                    "for another region..."
                )

                continue


            # NUMERICAL XYZ → SERVO IK


            try:

                ik_result = (
                    inverse_kinematics_detailed(
                        x,
                        y,
                        z,
                        max_adjustment_mm=
                            MAX_IK_ADJUSTMENT_MM
                    )
                )

            except ValueError as e:

                print()
                print(
                    "No reachable arm position "
                    "found within the allowed "
                    "adjustment."
                )

                print(
                    f"IK error: {e}"
                )

                print(
                    "Asking Position LLM "
                    "for another region..."
                )

                continue


            # Extract numerical IK result


            servo_result = ik_result["servo_angles"]

            base = float(servo_result["base"])
            shoulder = float(servo_result["shoulder"])
            elbow = float(servo_result["elbow"])

            reachable_xyz = (
                ik_result["reachable_xyz"]
            )

            adjustment_mm = (
                ik_result["adjustment_mm"]
            )

            reachable_x = reachable_xyz["x"]
            reachable_y = reachable_xyz["y"]
            reachable_z = reachable_xyz["z"]


            # Final servo safety clamp


            base = clamp_servo(base)
            shoulder = clamp_servo(shoulder)
            elbow = clamp_servo(elbow)


            # Print IK result


            print()
            
            
            print(
                "NUMERICAL IK RESULT"
            )
            
            print(
                "\nRequested XYZ:"
            )

            print(
                f"X = {x:.2f} mm"
            )

            print(
                f"Y = {y:.2f} mm"
            )

            print(
                f"Z = {z:.2f} mm"
            )

            print(
                "\nNearest reachable XYZ:"
            )

            print(
                f"X = {reachable_x:.2f} mm"
            )

            print(
                f"Y = {reachable_y:.2f} mm"
            )

            print(
                f"Z = {reachable_z:.2f} mm"
            )

            print(
                f"\nAdjustment = "
                f"{adjustment_mm:.2f} mm"
            )

            print(
                "\nServo target:"
            )

            print(
                f"Base     = {base:.2f}°"
            )

            print(
                f"Shoulder = {shoulder:.2f}°"
            )

            print(
                f"Elbow    = {elbow:.2f}°"
            )


            # Absolute final servo range check


            if not (
                0.0 <= base <= 90.0
                and
                0.0 <= shoulder <= 90.0
                and
                0.0 <= elbow <= 90.0
            ):

                print(
                    "\nSAFETY ERROR:"
                )

                print(
                    "IK generated a servo angle "
                    "outside 0–90°."
                )

                print(
                    "Target rejected."
                )

                continue


            # Store ACTUAL reachable position.
            #
            # This is important:
            # if IK adjusted the target, coverage and
            # spray protection should use the position
            # where the arm actually went.


            actual_xyz = {
                "x": float(reachable_x),
                "y": float(reachable_y),
                "z": float(reachable_z)
            }

            servo_angles = {
                "base":
                    round(base, 2),

                "shoulder":
                    round(shoulder, 2),

                "elbow":
                    round(elbow, 2)
            }


            # MOVE ARM


            print(
                "\nMoving arm to target..."
            )

            # Close position-planning camera
            # before detection_cycle uses camera.

            camera.close()

            reached = arduino.move(
                base,
                shoulder,
                elbow
            )

            if not reached:

                print(
                    "Arm did not reach target."
                )

                camera.open()

                continue

            print(
                "\nARM_REACHED."
            )


            # DETECTION MODE


            print()
            print("=" * 60)

            print(
                "STARTING DISEASE DETECTION"
            )

            print("=" * 60)

            current_view_id = (
                f"view_{view_number:03d}"
            )

            detection_result = (
                run_detection_cycle(
                    plant_id=PLANT_ID,
                    view_id=current_view_id
                )
            )

            if detection_result is None:

                print(
                    "\nDetection cycle cancelled."
                )

                break


            # RECORD VIEW


            coverage.add_view(
                view_id=current_view_id,

                pixel_x=pixel_x,
                pixel_y=pixel_y,

                distance_mm=distance_mm,

                # IMPORTANT:
                # Record the actual reachable position,
                # not the unreachable requested position.
                xyz=actual_xyz,

                servo_angles=servo_angles,

                detection_result=
                    detection_result,

                frame_paths=
                    detection_result.get(
                        "saved_frames",
                        []
                    )
            )


            # SPRAY PROTECTION


            if detection_result[
                "spray_needed"
            ]:

                print(
                    "\nDetection requested spraying."
                )


                # Check whether this physical region has already
                # been sprayed.


                if coverage.spray_already_done(
                    actual_xyz,
                    MIN_SPRAY_DISTANCE_MM
                ):

                    print(
                        "\nWARNING: This region was "
                        "already sprayed."
                    )

                    print(
                        "Duplicate spray BLOCKED."
                    )

                else:

                    duration = (
                        detection_result[
                            "duration"
                        ]
                    )

                    print(
                        "\nRegion has not been sprayed."
                    )

                    print(
                        f"Starting spray for "
                        f"{duration} seconds."
                    )


                    # ACTUAL SPRAY


                    spray_with_arduino(
                        duration
                    )


                    # Record spray only after the spray
                    # command has completed.


                    coverage.add_sprayed_region(
                        xyz=actual_xyz,
                        view_id=current_view_id
                    )

                    print(
                        "Sprayed region recorded."
                    )

            else:

                print(
                    "\nNo spraying required."
                )


            # RETURN TO POSITION MODE


            print(
                "\nReturning to "
                "position-planning mode..."
            )

            camera.open()

            view_number += 1


        # COVERAGE COMPLETE


        print()
        print("=" * 60)

        print(
            "PLANT COVERAGE COMPLETE"
        )

        print("=" * 60)

        print(
            f"Views completed: "
            f"{coverage.view_count}"
        )

        print(
            f"Sprayed regions: "
            f"{coverage.spray_count}"
        )


        # HOME


        print(
            "\nReturning arm to HOME..."
        )

        camera.close()

        arduino.home()

        print(
            "\nARM HOME REACHED."
        )

        print()
        print("=" * 60)

        print(
            "AUTOMATION COMPLETE"
        )

        print("=" * 60)

    finally:

        camera.close()
        arduino.close()



# ENTRY POINT


if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        print(
            "\nAutomation interrupted by user."
        )

    except Exception as e:

        print(
            "\n!!! AUTOMATION ERROR !!!"
        )

        print(e)

        raise
