import os
import json
import base64
import cv2
import requests


OPENROUTER_URL = (
    "https://openrouter.ai/api/v1/chat/completions"
)

MODEL = "inclusionai/ling-3.0-flash-vl:free"



# IMAGE ENCODING


def encode_frame(frame):

    success, buffer = cv2.imencode(
        ".jpg",
        frame
    )

    if not success:
        raise RuntimeError(
            "Could not encode camera frame"
        )

    encoded = base64.b64encode(
        buffer
    ).decode("utf-8")

    return (
        "data:image/jpeg;base64,"
        + encoded
    )



# POSITION PLANNER


def choose_next_position(
    frame,
    coverage_history
):

    api_key = os.getenv(
        "OPENROUTER_API_KEY"
    )

    if not api_key:

        raise RuntimeError(
            "OPENROUTER_API_KEY environment "
            "variable is not set"
        )

    history_text = json.dumps(
        coverage_history,
        indent=2
    )

    prompt = f"""
You are the positioning system for an agricultural
robotic plant inspection arm.

Your ONLY job is to choose the next visible plant
region that should be inspected.

You receive:
1. The current camera image.
2. A history of regions already viewed.
3. A history of regions already sprayed.

The robotic arm will move its nozzle/camera toward
the pixel you choose.

IMPORTANT RULES:

- Inspect the visible plant systematically.
- Do NOT repeatedly choose an already inspected region.
- Prefer a clearly visible plant region that has not
  yet been inspected.
- If only a small uncovered region remains, choose
  that region rather than making another large move.
- A region that was viewed but did not require spraying
  is still considered viewed.
- A region that was sprayed must never be selected again
  for spraying.
- Use the history to avoid returning to previous regions.
- Do not decide whether spraying is required.
- Do not determine spray duration.
- Do not calculate XYZ.
- Do not calculate servo angles.
- Only return a camera pixel.

Coverage history:

{history_text}

Image dimensions are exactly:

width = 640
height = 480

If an uncovered visible plant region remains, return:

{{
  "target_found": true,
  "target_pixel": {{
    "x": 412,
    "y": 285
  }},
  "target_type": "uncovered_region"
}}

If the visible plant has been sufficiently covered,
return:

{{
  "target_found": false,
  "target_pixel": null,
  "target_type": "coverage_complete"
}}

Return JSON ONLY.
"""

    content = [
        {
            "type": "text",
            "text": prompt
        },
        {
            "type": "image_url",
            "image_url": {
                "url": encode_frame(frame)
            }
        }
    ]

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
        OPENROUTER_URL,
        headers={
            "Authorization":
                f"Bearer {api_key}",
            "Content-Type":
                "application/json"
        },
        json=payload,
        timeout=60
    )

    if response.status_code != 200:

        print(
            "\n--- POSITION LLM ERROR ---"
        )

        print(
            response.text
        )

        response.raise_for_status()

    data = response.json()

    answer = (
        data["choices"][0]
        ["message"]["content"]
        .strip()
    )

    print(
        "\n--- POSITION LLM RESPONSE ---"
    )

    print(answer)


    # Remove markdown fences if present


    if answer.startswith("```"):

        answer = answer.replace(
            "```json",
            ""
        )

        answer = answer.replace(
            "```",
            ""
        )

        answer = answer.strip()

    result = json.loads(answer)


    # Validate result


    target_found = bool(
        result["target_found"]
    )

    if not target_found:

        return {
            "target_found": False,
            "target_pixel": None,
            "target_type":
                result.get(
                    "target_type",
                    "coverage_complete"
                )
        }

    pixel = result.get(
        "target_pixel"
    )

    if pixel is None:

        raise ValueError(
            "Position LLM said target_found=true "
            "but returned no target_pixel."
        )

    x = int(pixel["x"])
    y = int(pixel["y"])

    if not (
        0 <= x < 640
        and
        0 <= y < 480
    ):

        raise ValueError(
            f"Invalid target pixel: {x}, {y}"
        )

    return {
        "target_found": True,

        "target_pixel": {
            "x": x,
            "y": y
        },

        "target_type":
            result.get(
                "target_type",
                "uncovered_region"
            )
    }
