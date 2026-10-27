import os
import json
import math


DATA_DIRECTORY = os.path.expanduser(
    "~/leaf_model/plant_data"
)


class CoverageManager:

    def __init__(self, plant_id="plant_001"):

        self.plant_id = plant_id

        os.makedirs(
            DATA_DIRECTORY,
            exist_ok=True
        )

        self.file_path = os.path.join(
            DATA_DIRECTORY,
            f"{plant_id}.json"
        )

        self.data = self._load()


    # LOAD / SAVE


    def _load(self):

        if os.path.exists(self.file_path):

            try:

                with open(
                    self.file_path,
                    "r"
                ) as f:

                    return json.load(f)

            except Exception:

                pass

        return {
            "plant_id": self.plant_id,
            "views": [],
            "sprayed_regions": []
        }

    def save(self):

        with open(
            self.file_path,
            "w"
        ) as f:

            json.dump(
                self.data,
                f,
                indent=2
            )


    # DISTANCE BETWEEN XYZ POINTS


    @staticmethod
    def xyz_distance(a, b):

        if a is None or b is None:
            return float("inf")

        return math.sqrt(
            (a["x"] - b["x"]) ** 2 +
            (a["y"] - b["y"]) ** 2 +
            (a["z"] - b["z"]) ** 2
        )


    # VIEW HISTORY


    def add_view(
        self,
        view_id,
        pixel_x,
        pixel_y,
        distance_mm,
        xyz,
        servo_angles,
        detection_result,
        frame_paths=None
    ):

        view = {
            "view_id": view_id,

            "pixel": {
                "x": int(pixel_x),
                "y": int(pixel_y)
            },

            "distance_mm":
                float(distance_mm),

            "xyz": xyz,

            "servo_angles":
                servo_angles,

            "detection": {
                "spray_needed":
                    detection_result.get(
                        "spray_needed"
                    ),
                "duration":
                    detection_result.get(
                        "duration"
                    )
            },

            "frame_paths":
                frame_paths or []
        }

        self.data["views"].append(
            view
        )

        self.save()


    # WAS THIS AREA ALREADY VIEWED?


    def position_already_viewed(
        self,
        xyz,
        minimum_distance_mm=30.0
    ):

        for view in self.data["views"]:

            old_xyz = view.get("xyz")

            if self.xyz_distance(
                xyz,
                old_xyz
            ) < minimum_distance_mm:

                return True

        return False


    # SPRAY HISTORY


    def add_sprayed_region(
        self,
        xyz,
        disease_name=None,
        view_id=None
    ):

        region = {
            "xyz": xyz,
            "disease_name":
                disease_name,
            "view_id":
                view_id
        }

        self.data[
            "sprayed_regions"
        ].append(region)

        self.save()


    # WAS THIS AREA ALREADY SPRAYED?


    def spray_already_done(
        self,
        xyz,
        minimum_distance_mm=30.0
    ):

        for region in self.data[
            "sprayed_regions"
        ]:

            old_xyz = region.get("xyz")

            if self.xyz_distance(
                xyz,
                old_xyz
            ) < minimum_distance_mm:

                return True

        return False


    # COUNTERS


    @property
    def view_count(self):

        return len(
            self.data["views"]
        )

    @property
    def spray_count(self):

        return len(
            self.data["sprayed_regions"]
        )


    # HISTORY FOR POSITION LLM


    def get_history_for_llm(self):

        return {
            "views": [
                {
                    "view_id":
                        v["view_id"],
                    "pixel":
                        v["pixel"],
                    "xyz":
                        v["xyz"],
                    "spray_needed":
                        v["detection"]
                        ["spray_needed"]
                }
                for v in self.data["views"]
            ],

            "sprayed_regions": [
                {
                    "xyz":
                        r["xyz"],
                    "disease_name":
                        r.get(
                            "disease_name"
                        )
                }
                for r in
                self.data[
                    "sprayed_regions"
                ]
            ]
        }
