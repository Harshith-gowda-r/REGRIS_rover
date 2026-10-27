import cv2
import numpy as np
import glob
import os

CHECKERBOARD = (9, 6)
SQUARE_SIZE = 6.4  # mm

IMAGE_DIR = "calibration_images"
OUTPUT_FILE = "camera_calibration.npz"


# Create 3D coordinates of checkerboard corners


objp = np.zeros(
    (CHECKERBOARD[0] * CHECKERBOARD[1], 3),
    np.float32
)

objp[:, :2] = np.mgrid[
    0:CHECKERBOARD[0],
    0:CHECKERBOARD[1]
].T.reshape(-1, 2)

objp *= SQUARE_SIZE

object_points = []
image_points = []


# Find calibration images


images = sorted(
    glob.glob(os.path.join(IMAGE_DIR, "*.jpg"))
)

print("=" * 60)
print("CAMERA CALIBRATION")
print("=" * 60)

print(f"Images found: {len(images)}")
print(
    f"Checkerboard: "
    f"{CHECKERBOARD[0]} x {CHECKERBOARD[1]}"
)
print(f"Square size: {SQUARE_SIZE} mm")

image_size = None
valid = 0


# Detect checkerboard corners


for filename in images:

    image = cv2.imread(filename)

    if image is None:
        print("Could not read:", filename)
        continue

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    if image_size is None:
        image_size = gray.shape[::-1]

    found, corners = cv2.findChessboardCorners(
        gray,
        CHECKERBOARD,
        None
    )

    if found:

        criteria = (
            cv2.TERM_CRITERIA_EPS
            + cv2.TERM_CRITERIA_MAX_ITER,
            30,
            0.001
        )

        corners = cv2.cornerSubPix(
            gray,
            corners,
            (11, 11),
            (-1, -1),
            criteria
        )

        object_points.append(objp)
        image_points.append(corners)

        valid += 1

        print(
            f"VALID: "
            f"{os.path.basename(filename)}"
        )

    else:

        print(
            f"INVALID: "
            f"{os.path.basename(filename)}"
        )


# Check number of valid images


print()
print(f"Valid calibration images: {valid}")

if valid < 10:

    print(
        "ERROR: Not enough valid calibration images."
    )

    exit()


# Camera calibration


print()
print("Calculating camera parameters...")

ret, camera_matrix, distortion, rvecs, tvecs = (
    cv2.calibrateCamera(
        object_points,
        image_points,
        image_size,
        None,
        None
    )
)


# Calculate reprojection error


total_error = 0

for i in range(len(object_points)):

    projected_points, _ = cv2.projectPoints(
        object_points[i],
        rvecs[i],
        tvecs[i],
        camera_matrix,
        distortion
    )

    # Convert both arrays to Nx2
    detected = image_points[i].reshape(-1, 2)
    projected = projected_points.reshape(-1, 2)

    error = cv2.norm(
        detected,
        projected,
        cv2.NORM_L2
    ) / len(projected)

    total_error += error

mean_error = (
    total_error / len(object_points)
)


# Print results


print()
print("=" * 60)
print("CALIBRATION RESULTS")
print("=" * 60)

print()
print(
    f"Image size: "
    f"{image_size[0]} x {image_size[1]}"
)

print()
print("Camera Matrix:")
print(camera_matrix)

print()
print("Distortion Coefficients:")
print(distortion.ravel())

print()
print(
    f"RMS calibration error: "
    f"{ret:.4f}"
)

print(
    f"Mean reprojection error: "
    f"{mean_error:.4f} pixels"
)


# Save calibration


np.savez(
    OUTPUT_FILE,
    camera_matrix=camera_matrix,
    distortion=distortion,
    image_width=image_size[0],
    image_height=image_size[1],
    square_size=SQUARE_SIZE,
    rms_error=ret,
    mean_error=mean_error
)

print()
print("Calibration saved to:")
print(OUTPUT_FILE)

print()
print("=" * 60)
print("CALIBRATION COMPLETE")
print("=" * 60)
