import serial
import time
from inverse_kinematics import inverse_kinematics

PORT = "/dev/ttyUSB0"
BAUD = 115200

ser = serial.Serial(PORT, BAUD, timeout=2)
time.sleep(2)


def move_to_xyz(x, y, z):

    print(f"Target XYZ: X={x} Y={y} Z={z}")

    try:
        base, shoulder, elbow = inverse_kinematics(x, y, z)
    except ValueError as e:
        print("IK ERROR:", e)
        return

    base = round(base)
    shoulder = round(shoulder)
    elbow = round(elbow)

    print(
        f"Calculated servo angles: "
        f"Base={base}° "
        f"Shoulder={shoulder}° "
        f"Elbow={elbow}°"
    )

    command = f"MOVE {base} {shoulder} {elbow}\n"

    print("Sending:", command.strip())
    ser.write(command.encode())

    start = time.time()

    while time.time() - start < 10:
        line = ser.readline().decode(errors="ignore").strip()

        if line:
            print("Arduino:", line)

            if line == "ARM_REACHED":
                print("Target reached.")
                break


try:

    print("\nStarting physical IK test...")
    print("Make sure the arm has enough clear space.")

    # Start from HOME
    print("\nMoving to HOME...")
    ser.write(b"HOME\n")

    while True:
        line = ser.readline().decode(errors="ignore").strip()

        if line:
            print("Arduino:", line)

        if line == "HOME_REACHED":
            break

    time.sleep(2)

    # TEST 1
    move_to_xyz(200, 0, 85)
    time.sleep(2)

    input("\nCheck TEST 1 physically. Press ENTER for TEST 2...")

    # TEST 2
    move_to_xyz(180, 0, 60)
    time.sleep(2)

    input("\nCheck TEST 2 physically. Press ENTER for TEST 3...")

    # TEST 3
    move_to_xyz(180, 50, 60)
    time.sleep(2)

    input("\nPress ENTER to return HOME...")

    ser.write(b"HOME\n")

    while True:
        line = ser.readline().decode(errors="ignore").strip()

        if line:
            print("Arduino:", line)

        if line == "HOME_REACHED":
            break

    print("\nPhysical IK test complete.")

finally:
    ser.close()
