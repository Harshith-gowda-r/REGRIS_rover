import serial
import time
from inverse_kinematics import inverse_kinematics

PORT = "/dev/ttyUSB0"
BAUD = 115200

ser = serial.Serial(PORT, BAUD, timeout=2)
time.sleep(2)


def wait_for(message, timeout=10):
    start = time.time()

    while time.time() - start < timeout:
        line = ser.readline().decode(errors="ignore").strip()

        if line:
            print("Arduino:", line)

            if line == message:
                return True

    return False


def move_xyz(x, y, z):

    print(f"TARGET XYZ = ({x:.2f}, {y:.2f}, {z:.2f})")

    base, shoulder, elbow = inverse_kinematics(x, y, z)

    base = round(base)
    shoulder = round(shoulder)
    elbow = round(elbow)

    print(
        f"IK -> Base={base}° "
        f"Shoulder={shoulder}° "
        f"Elbow={elbow}°"
    )

    command = f"MOVE {base} {shoulder} {elbow}\n"

    print("Sending:", command.strip())

    ser.write(command.encode())

    if wait_for("ARM_REACHED"):
        print("TARGET REACHED")
    else:
        print("WARNING: ARM_REACHED not received")


try:

    print("Starting physical XYZ test.")
    print("Make sure the arm has clear space.")

    # HOME
    print("\nMoving HOME...")
    ser.write(b"HOME\n")
    wait_for("HOME_REACHED")

    time.sleep(2)

    input(
        "\nPress ENTER to move to TEST 1 "
        "(209.2, 0, 66.7)..."
    )

    # TEST 1
    move_xyz(209.20, 0, 66.70)

    input(
        "\nInspect the arm position physically. "
        "Press ENTER to return HOME..."
    )

    ser.write(b"HOME\n")
    wait_for("HOME_REACHED")

    time.sleep(2)

    input(
        "\nPress ENTER to move to TEST 2 "
        "(192.94, 51.70, 26.13)..."
    )

    # TEST 2
    move_xyz(192.94, 51.70, 26.13)

    input(
        "\nInspect the arm position physically. "
        "Press ENTER to return HOME..."
    )

    ser.write(b"HOME\n")
    wait_for("HOME_REACHED")

    print("\nPhysical XYZ test complete.")

finally:
    ser.close()
