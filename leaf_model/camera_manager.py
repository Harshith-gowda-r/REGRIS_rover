import cv2
import time


class CameraManager:

    def __init__(
        self,
        device="/dev/video2",
        width=640,
        height=480
    ):

        self.device = device
        self.width = width
        self.height = height
        self.cap = None



    # OPEN CAMERA


    def open(self):

        if self.cap is not None:
            return

        self.cap = cv2.VideoCapture(
            self.device,
            cv2.CAP_V4L2
        )

        if not self.cap.isOpened():

            self.cap = None

            raise RuntimeError(
                f"Could not open camera {self.device}"
            )

        self.cap.set(
            cv2.CAP_PROP_FRAME_WIDTH,
            self.width
        )

        self.cap.set(
            cv2.CAP_PROP_FRAME_HEIGHT,
            self.height
        )

        # Allow camera to stabilize
        time.sleep(1)



    # CAPTURE ONE FRAME


    def read(self):

        if self.cap is None:
            self.open()

        ret, frame = self.cap.read()

        if not ret:

            raise RuntimeError(
                "Could not read camera frame"
            )

        return frame



    # CAPTURE STABLE FRAME


    def capture_stable_frame(
        self,
        discard_frames=5
    ):

        if self.cap is None:
            self.open()

        frame = None

        for _ in range(discard_frames):

            ret, frame = self.cap.read()

            if not ret:

                raise RuntimeError(
                    "Camera frame failed"
                )

            time.sleep(0.03)

        return frame



    # CLOSE CAMERA


    def close(self):

        if self.cap is not None:

            self.cap.release()

            self.cap = None
