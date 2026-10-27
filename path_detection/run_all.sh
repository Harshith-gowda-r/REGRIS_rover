#!/bin/bash

cd ~/path_detection
source venv/bin/activate

echo "Starting bridge..."
python bridge.py &
BRIDGE_PID=$!

echo "Starting path detection..."
python path_detect.py &
PATH_PID=$!

echo "Starting WebRTC..."
python webrtc_stream.py &
WEBRTC_PID=$!

echo ""
echo "================================"
echo " REGRIS Rover System Started"
echo "================================"
echo "Bridge PID: $BRIDGE_PID"
echo "Path Detection PID: $PATH_PID"
echo "WebRTC PID: $WEBRTC_PID"
echo ""
echo "Press Ctrl+C to stop everything."

trap 'kill $BRIDGE_PID $PATH_PID $WEBRTC_PID 2>/dev/null; exit' INT TERM

wait
