# REGRIS Rover

## Agricultural Rover for Plant Detection, Path Detection and Robotic Automation

REGRIS is an agricultural rover system combining computer vision, path
detection, plant detection, robotic-arm control, inverse kinematics,
and remote communication.

The system is organized into two major software modules:

- `leaf_model` – plant/leaf detection and robotic-arm automation
- `path_detection` – rover path detection, WebRTC streaming and Firebase communication

---

## System Architecture

```text
                    REGRIS ROVER
                         |
          +--------------+--------------+
          |                             |
          v                             v
    leaf_model                    path_detection
          |                             |
          v                             v
   Plant Detection                Path Detection
          |                             |
          v                             v
   YOLO Inference                 Camera Processing
          |                             |
          v                             v
   Position Estimation            Direction Detection
          |                             |
          v                             v
   Inverse Kinematics             Rover Navigation
          |                             |
          v                             v
    Robotic Arm                   WebRTC / Firebase
          |
          v
   Arduino Controller
