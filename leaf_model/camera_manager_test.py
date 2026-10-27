from camera_manager import CameraManager

camera = CameraManager()

print("Opening camera...")

camera.open()

print("Capturing frame...")

frame = camera.capture_stable_frame()

print(
    "Frame received:",
    frame.shape
)

camera.close()

print("Camera closed.")
