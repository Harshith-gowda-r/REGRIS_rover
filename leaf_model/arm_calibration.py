import serial
import time

PORT = "/dev/ttyUSB0"
BAUD = 115200

ser = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(2)


print("       ARM CALIBRATION")

print("Commands:")
print("  home")
print("  base <0-90>")
print("  shoulder <0-90>")
print("  elbow <0-90>")
print("  move <base> <shoulder> <elbow>")
print("  status")
print("  exit")



def read_responses(wait_for_reached=False):
    while True:
        line = ser.readline().decode(errors="ignore").strip()

        if not line:
            break

        print("Arduino:", line)

        if wait_for_reached and line in ("ARM_REACHED", "HOME_REACHED"):
            break


def send(command):
    print("Laptop:", command)

    ser.write((command + "\n").encode())

    if command.startswith("move") or command == "home":
        read_responses(wait_for_reached=True)
    else:
        time.sleep(0.1)
        read_responses()


try:

    while True:

        command = input("ARM > ").strip()

        if not command:
            continue

        parts = command.split()

        if parts[0].lower() == "exit":
            break

        elif parts[0].lower() == "home":
            send("HOME")

        elif parts[0].lower() == "base" and len(parts) == 2:
            angle = int(parts[1])
            if 0 <= angle <= 90:
                send(f"SERVO BASE {angle}")
            else:
                print("Base must be 0-90°")

        elif parts[0].lower() == "shoulder" and len(parts) == 2:
            angle = int(parts[1])
            if 0 <= angle <= 90:
                send(f"SERVO SHOULDER {angle}")
            else:
                print("Shoulder must be 0-90°")

        elif parts[0].lower() == "elbow" and len(parts) == 2:
            angle = int(parts[1])
            if 0 <= angle <= 90:
                send(f"SERVO ELBOW {angle}")
            else:
                print("Elbow must be 0-90°")

        elif parts[0].lower() == "move" and len(parts) == 4:

            base = int(parts[1])
            shoulder = int(parts[2])
            elbow = int(parts[3])

            if all(0 <= x <= 90 for x in (base, shoulder, elbow)):
                send(f"MOVE {base} {shoulder} {elbow}")
            else:
                print("All angles must be 0-90°")

        elif parts[0].lower() == "status":
            send("STATUS")

        else:
            print("Unknown command")

finally:
    ser.close()
    print("Serial connection closed.")
