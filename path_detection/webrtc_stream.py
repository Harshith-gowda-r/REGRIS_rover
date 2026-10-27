import asyncio
import threading
import time
import os
import cv2
import av
import numpy as np

import firebase_admin
from firebase_admin import credentials, db

from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    VideoStreamTrack,
    RTCConfiguration,
    RTCIceServer
)

from path_detect import process_path_frame



# CONFIGURATION


CAMERA_DEVICE = "/dev/video2"

WIDTH = 640
HEIGHT = 480
FPS = 30

SERVICE_ACCOUNT = os.getenv(
    "FIREBASE_SERVICE_ACCOUNT",
    "regris_ds.json"
)

DATABASE_URL = (
    "https://regris-dashboard-default-rtdb."
    "asia-southeast1.firebasedatabase.app/"
)

ROVER_ID = "REGRIS-01"



# FIREBASE INITIALIZATION


cred = credentials.Certificate(SERVICE_ACCOUNT)

if not firebase_admin._apps:
    firebase_admin.initialize_app(
        cred,
        {
            "databaseURL": DATABASE_URL
        }
    )

rover_db = db.reference(ROVER_ID)

print()

print("       REGRIS PATH DETECTION WEBRTC")

print("[Firebase] Connected")
print()



# SHARED CAMERA


class SharedCamera:

    def __init__(self):

        self.cap = None
        self.running = False
        self.thread = None

        self.lock = threading.Lock()

        self.processed_frame = None

        self.direction = "PATH LOST"
        self.error = 0
        self.path_found = False


    # START CAMERA


    def start(self):

        if self.running:
            return

        print(
            f"[Camera] Opening {CAMERA_DEVICE}"
        )

        self.cap = cv2.VideoCapture(
            CAMERA_DEVICE,
            cv2.CAP_V4L2
        )

        if not self.cap.isOpened():

            raise RuntimeError(
                f"Cannot open camera {CAMERA_DEVICE}"
            )

        # Try YUYV format
        self.cap.set(
            cv2.CAP_PROP_FOURCC,
            cv2.VideoWriter_fourcc(*"YUYV")
        )

        self.cap.set(
            cv2.CAP_PROP_FRAME_WIDTH,
            WIDTH
        )

        self.cap.set(
            cv2.CAP_PROP_FRAME_HEIGHT,
            HEIGHT
        )

        self.cap.set(
            cv2.CAP_PROP_FPS,
            FPS
        )

        self.running = True

        self.thread = threading.Thread(
            target=self.capture_loop,
            daemon=True
        )

        self.thread.start()

        print(
            "[Camera] /dev/video2 opened successfully"
        )

        print(
            "[Camera] Path detection started"
        )


    # CAMERA CAPTURE LOOP


    def capture_loop(self):

        print(
            "[Camera] Capture loop running"
        )

        while self.running:

            ret, frame = self.cap.read()

            if not ret:

                print(
                    "[Camera] Frame read error"
                )

                time.sleep(0.05)

                continue

            try:

                # path_detect.py returns:
                #
                # processed_frame
                # direction
                # error
                # path_found

                (
                    processed,
                    direction,
                    error,
                    path_found
                ) = process_path_frame(frame)

            except Exception as e:

                print(
                    f"[Path Detection] ERROR: {e}"
                )

                processed = frame.copy()

                direction = "PATH LOST"

                error = 0

                path_found = False


            # Store latest processed frame and detection data


            with self.lock:

                self.processed_frame = (
                    processed.copy()
                )

                self.direction = direction

                self.error = error

                self.path_found = path_found

        print(
            "[Camera] Capture loop stopped"
        )


    # GET LATEST FRAME


    def get_frame(self):

        with self.lock:

            if self.processed_frame is None:

                return None

            return self.processed_frame.copy()


    # GET PATH COMMAND


    def get_command(self):

        with self.lock:

            return (
                self.direction,
                self.error,
                self.path_found
            )


    # STOP CAMERA


    def stop(self):

        if not self.running:
            return

        print(
            "[Camera] Stopping..."
        )

        self.running = False

        if self.thread:

            self.thread.join(
                timeout=2
            )

        if self.cap:

            self.cap.release()

        self.cap = None

        print(
            "[Camera] Hardware released"
        )



# CREATE AND START CAMERA


camera = SharedCamera()

camera.start()



# WEBRTC VIDEO TRACK


class PathVideoTrack(VideoStreamTrack):

    def __init__(self):

        super().__init__()

        print(
            "[WebRTC] Path video track created"
        )

    async def recv(self):

        pts, time_base = (
            await self.next_timestamp()
        )

        frame = camera.get_frame()

        # If camera frame is not ready
        if frame is None:

            frame = np.zeros(
                (
                    HEIGHT,
                    WIDTH,
                    3
                ),
                dtype=np.uint8
            )

        # BGR -> RGB
        frame_rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        video_frame = (
            av.VideoFrame.from_ndarray(
                frame_rgb,
                format="rgb24"
            )
        )

        video_frame.pts = pts

        video_frame.time_base = time_base

        return video_frame



# WEBRTC ASYNCIO LOOP


webrtc_loop = asyncio.new_event_loop()


def run_webrtc_loop():

    asyncio.set_event_loop(
        webrtc_loop
    )

    webrtc_loop.run_forever()


webrtc_thread = threading.Thread(
    target=run_webrtc_loop,
    daemon=True
)

webrtc_thread.start()



# ACTIVE WEBRTC CONNECTION


active_pc = None



# PROCESS WEBRTC OFFER


async def process_offer(offer_data):

    global active_pc

    print()


    print(
        "[WebRTC] Path detection offer received"
    )
    


    # Close previous connection


    if active_pc is not None:

        print(
            "[WebRTC] Closing previous connection..."
        )

        old_pc = active_pc

        active_pc = None

        try:

            await old_pc.close()

        except Exception as e:

            print(
                f"[WebRTC] Previous connection close: {e}"
            )

        await asyncio.sleep(0.2)


    # WebRTC configuration


    config = RTCConfiguration(
        iceServers=[
            RTCIceServer(
                urls=[
                    "stun:stun.l.google.com:19302"
                ]
            )
        ]
    )

    pc = RTCPeerConnection(
        configuration=config
    )

    active_pc = pc


    # Add processed path video


    pc.addTrack(
        PathVideoTrack()
    )


    # Connection state monitoring


    @pc.on("connectionstatechange")
    async def on_connectionstatechange():

        global active_pc

        print(
            f"[WebRTC] Connection state: "
            f"{pc.connectionState}"
        )

        if pc.connectionState in [
            "failed",
            "closed"
        ]:

            if active_pc == pc:

                active_pc = None


    # Set browser offer


    try:

        offer = RTCSessionDescription(
            sdp=offer_data["sdp"],
            type=offer_data["type"]
        )

        await pc.setRemoteDescription(
            offer
        )

    except Exception as e:

        print(
            f"[WebRTC] Invalid offer: {e}"
        )

        if active_pc == pc:

            active_pc = None

        try:

            await pc.close()

        except Exception:
            pass

        return


    # Create answer


    try:

        answer = await pc.createAnswer()

        await pc.setLocalDescription(
            answer
        )

    except Exception as e:

        print(
            f"[WebRTC] Answer error: {e}"
        )

        if active_pc == pc:

            active_pc = None

        try:

            await pc.close()

        except Exception:
            pass

        return


    # Wait for ICE gathering


    print(
        "[WebRTC] Gathering ICE..."
    )

    while (
        pc.iceGatheringState != "complete"
    ):

        await asyncio.sleep(0.1)


    # Send answer to Firebase


    try:

        rover_db.child(
            "webrtc/answer"
        ).set(
            {
                "sdp": pc.localDescription.sdp,
                "type": pc.localDescription.type,
                "timestamp": int(
                    time.time() * 1000
                )
            }
        )

        print(
            "[WebRTC] Answer sent to Firebase"
        )

        print(
            "[WebRTC] PATH DETECTION STREAM LIVE"
        )

        print()

    except Exception as e:

        print(
            f"[Firebase] Answer error: {e}"
        )



# FIREBASE OFFER CALLBACK


def on_offer_received(event):

    data = event.data

    if not data:
        return

    if not isinstance(
        data,
        dict
    ):
        return

    if data.get("type") != "offer":
        return

    print(
        "[Firebase] Offer received"
    )

    asyncio.run_coroutine_threadsafe(
        process_offer(data),
        webrtc_loop
    )



# FIREBASE LISTENER


print(
    "[Firebase] Listening for path detection offers..."
)

rover_db.child(
    "webrtc/offer"
).listen(
    on_offer_received
)



# SERVER READY


print()

print(
    "       PATH DETECTION SERVER READY"
)


print(
    "Camera : /dev/video2"
)

print(
    "Stream : PATH DETECTION ONLY"
)

print(
    "Firebase: REGRIS-01/webrtc/offer"
)

print(
    "Firebase: REGRIS-01/webrtc/answer"
)

print()

print(
    "CAMERA COMMANDS:"
)

print(
    "  SHARP LEFT"
)

print(
    "  LEFT"
)

print(
    "  FORWARD"
)

print(
    "  RIGHT"
)

print(
    "  SHARP RIGHT"
)

print(
    "  PATH LOST"
)

print()

print(
    "Camera does NOT directly control motors."
)

print(
    "Ultrasonic/navigation system controls movement."
)





# KEEP SERVER RUNNING


try:

    while True:

        time.sleep(1)

except KeyboardInterrupt:

    print()
    print(
        "[System] Shutdown requested..."
    )

finally:

    async def cleanup():

        global active_pc

        # Close WebRTC connection
        if active_pc is not None:

            pc = active_pc

            active_pc = None

            try:

                await pc.close()

            except Exception:
                pass

        # Stop camera
        camera.stop()

    future = (
        asyncio.run_coroutine_threadsafe(
            cleanup(),
            webrtc_loop
        )
    )

    try:

        future.result(
            timeout=5
        )

    except Exception:
        pass

    try:

        webrtc_loop.call_soon_threadsafe(
            webrtc_loop.stop
        )

    except Exception:
        pass

    print(
        "[System] Server stopped."
    )
