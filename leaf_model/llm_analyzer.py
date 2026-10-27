import os
import json
import base64
import requests


EXPERIENTIAL_URL = "https://api.experientiallabs.ai/v1/chat/completions"

MODEL = "gpt-5.6-luna"

def encode_frame(frame):
    import cv2

    success, buffer = cv2.imencode(".jpg", frame)

    if not success:
        raise RuntimeError("Could not encode frame")

    encoded = base64.b64encode(buffer).decode("utf-8")

    return f"data:image/jpeg;base64,{encoded}"


def analyze_with_llm(frames, detections):

    api_key = os.getenv("EXPLABS_API_KEY")

    if not api_key:
        raise RuntimeError(
            "EXPLABS_API_KEY environment variable is not set"
        )

    # Convert all YOLO information to readable text
    yolo_text = json.dumps(
        detections,
        indent=2
    )

    content = [
        {
            "type": "text",
            "text": f"""
You are the verification and decision system for a crop disease
detection system.

The YOLO model analysed a continuous 2-second observation of a plant.

Below is ALL YOLO detection information collected during that
observation:

{yolo_text}

You will also receive the LAST 6 camera frames from the observation.

Your tasks:

1. Inspect ALL supplied images.
2. Independently determine whether a disease/pest is visibly present.
3. Cross-check the visual evidence against the YOLO detections.
4. Do NOT blindly trust the YOLO prediction.
5. Identify the disease or pest visible in the plant.
6. If no disease or pest is visibly present, set disease_name to "None".
7. Decide whether spraying is actually necessary.
8. If spraying is necessary, determine the disease intensity.
9. Choose a spray duration from 7 to 15 seconds based on disease
   intensity.
10. If spraying is not necessary, set duration to null.
11. If no disease or pest is visible, set intensity to "none".

Allowed intensity values:

very_mild
mild
moderate
severe
very_severe
none

SEVERITY_DURATION:

very_mild: 7
mild: 8
moderate: 10
severe: 12
very_severe: 15

Return JSON ONLY using exactly this structure:

{{
  "disease_name": "Powdery Mildew Leaf",
  "intensity": "moderate",
  "spray_needed": true,
  "duration": 10
}}

OR when the plant is healthy:

{{
  "disease_name": "None",
  "intensity": "none",
  "spray_needed": false,
  "duration": null
}}

Rules:

- disease_name must be the detected disease or pest name.
- If there is no visible disease or pest, use "None".
- intensity must be one of:
  very_mild, mild, moderate, severe, very_severe, none
- If spray_needed is false, duration MUST be null.
- If spray_needed is true, duration MUST be an integer between 7 and 15.
- Return JSON ONLY.
"""
        }
    ]

    # Add the six images
    for frame in frames:
        image_data = encode_frame(frame)

        content.append({
            "type": "image_url",
            "image_url": {
                "url": image_data
            }
        })

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "user",
                "content": content
            }
        ],
        "temperature": 0.1
    }

    response = requests.post(
        EXPERIENTIAL_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json=payload,
        timeout=60
    )

    if response.status_code != 200:
        print("\n--- OPENROUTER ERROR ---")
        print("HTTP status:", response.status_code)
        print(response.text)
        response.raise_for_status()

    data = response.json()

    if "choices" not in data:
        print("\n--- OPENROUTER RESPONSE WITHOUT CHOICES ---")
        print(json.dumps(data, indent=2))
        raise RuntimeError(
            "OpenRouter did not return a valid LLM response"
        )

    answer = data["choices"][0]["message"]["content"]

    print("\n--- RAW LLM RESPONSE ---")
    print(answer)

    return answer


def parse_decision(answer):

    # Remove possible markdown code fences
    answer = answer.strip()

    if answer.startswith("```"):
        answer = answer.replace("```json", "")
        answer = answer.replace("```", "")
        answer = answer.strip()

    decision = json.loads(answer)


    # DISEASE INFORMATION


    disease_name = decision.get(
        "disease_name",
        "None"
    )

    intensity = decision.get(
        "intensity",
        "none"
    )

    # Ensure values are strings
    disease_name = str(disease_name)
    intensity = str(intensity).lower()


    # SPRAY DECISION


    spray_needed = bool(
        decision["spray_needed"]
    )

    duration = decision.get("duration")

    if spray_needed:

        if duration is None:
            raise ValueError(
                "LLM said spray is needed but gave no duration"
            )

        duration = int(duration)

        # HARD SAFETY LIMIT
        duration = max(7, min(15, duration))

    else:

        duration = None


    # FINAL DECISION

    return {
        "disease_name": disease_name,
        "intensity": intensity,
        "spray_needed": spray_needed,
        "duration": duration
    }
