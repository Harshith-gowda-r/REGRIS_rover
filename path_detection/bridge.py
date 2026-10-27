import asyncio
import threading
import time
import cv2
import av
import firebase_admin
from firebase_admin import credentials, db
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack, RTCConfiguration, RTCIceServer


# 1. INITIALIZE FIREBASE

import os

FIREBASE_SERVICE_ACCOUNT = os.getenv(
    "FIREBASE_SERVICE_ACCOUNT",
    "regris_ds.json"
)

cred = credentials.Certificate(FIREBASE_SERVICE_ACCOUNT)
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://regris-dashboard-default-rtdb.asia-southeast1.firebasedatabase.app/'
    })

rover_db = db.reference('REGRIS-01')
print("Rover connected to the cloud whiteboard!")


# 2. MOTOR CONTROL LISTENER

def handle_joystick(event):
    data = event.data
    if data and isinstance(data, dict):
        throttle = data.get('throttle', 0)
        steering = data.get('steering', 0)
        print(f"Website commands -> Throttle: {throttle}, Steering: {steering}")
        # smartelex.set_speed(throttle, steering)

rover_db.child('commands/drive').listen(handle_joystick)


# 3. OPENCV WEBRTC VIDEO PIPELINE

class OpenCVCameraTrack(VideoStreamTrack):
    def __init__(self):
        super().__init__()
        # Initialize OpenCV Camera
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

    async def recv(self):
        pts, time_base = await self.next_timestamp()
        ret, frame = self.cap.read()
        
        if not ret:
            # If OpenCV fails to grab a frame, wait slightly to avoid crashing
            await asyncio.sleep(0.05)
            import numpy as np
            frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # Convert OpenCV BGR to WebRTC RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        video_frame = av.VideoFrame.from_ndarray(frame_rgb, format="rgb24")
        video_frame.pts = pts
        video_frame.time_base = time_base
        return video_frame

# Create a persistent background thread for WebRTC
webrtc_loop = asyncio.new_event_loop()

def run_webrtc_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

threading.Thread(target=run_webrtc_loop, args=(webrtc_loop,), daemon=True).start()

async def process_offer(offer_data):
    print("[WebRTC] Received offer. Building OpenCV P2P link...")
    config = RTCConfiguration(iceServers=[RTCIceServer(urls=["stun:stun.l.google.com:19302"])])
    pc = RTCPeerConnection(configuration=config)
    
    # Attach the custom OpenCV track
    pc.addTrack(OpenCVCameraTrack())

    # Apply browser offer
    offer = RTCSessionDescription(sdp=offer_data['sdp'], type=offer_data['type'])
    await pc.setRemoteDescription(offer)

    # Create and send answer
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    rover_db.child('webrtc/answer').set({
        'sdp': pc.localDescription.sdp,
        'type': pc.localDescription.type,
        'timestamp': int(time.time() * 1000)
    })
    print("[WebRTC] Answer transmitted. OpenCV stream is LIVE!")

def on_offer_received(event):
    data = event.data
    if data and isinstance(data, dict) and data.get('type') == 'offer':
        # Send the task to the permanent background thread so it doesn't die
        asyncio.run_coroutine_threadsafe(process_offer(data), webrtc_loop)

print("[WebRTC] Rover video daemon initialized. Waiting for dashboard...")
rover_db.child('webrtc/offer').listen(on_offer_received)


# 4. TELEMETRY MAIN LOOP

while True:
    try:
        current_tank = 60  # Replace with actual tank sensor logic
        rover_db.child('hardware').update({'tank_pct': current_tank})
        print(f"Sent to website: Tank {current_tank}%")
    except Exception as e:
        pass
    time.sleep(1)
