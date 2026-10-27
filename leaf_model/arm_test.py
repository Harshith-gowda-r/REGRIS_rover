import serial
import time

PORT = "/dev/ttyUSB0"
BAUD = 115200

ser = serial.Serial(PORT, BAUD, timeout=1)

time.sleep(2)

def send(command):
    print(">>>", command)

    ser.write((command + "\n").encode())

    while True:
        response = ser.readline().decode(errors="ignore").strip()

        if response:
            print("<<<", response)

            if response in ["ARM_REACHED", "HOME_REACHED"]:
                break


print("Arduino connected")

send("HOME")

time.sleep(1)

send("MOVE 60 80 60")

time.sleep(1)

send("HOME")

ser.close()
