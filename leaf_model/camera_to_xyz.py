import math



# CAMERA CALIBRATION


FX = 933.98727168
FY = 968.37797809

CX = 349.17260579
CY = 346.05759238



# CAMERA → NOZZLE OFFSET


# Camera is 55 mm ABOVE the nozzle.
CAMERA_TO_NOZZLE_Z = 55.0



# CAMERA PIXEL → ROVER XYZ


def camera_pixel_to_xyz(
    pixel_x,
    pixel_y,
    distance_mm
):
    """
    Convert a camera pixel and measured distance
    into rover XYZ coordinates.

    Coordinate system:

        +X = forward
        +Y = left
        +Z = up

    Camera coordinate system:

        +Z = forward
        +X = right
        +Y = down

    Camera is mounted 55 mm above the nozzle.
    """

    u = float(pixel_x)
    v = float(pixel_y)
    z_cam = float(distance_mm)


    # Camera coordinate

    x_cam = (
        (u - CX)
        * z_cam
        / FX
    )

    y_cam = (
        (v - CY)
        * z_cam
        / FY
    )


    # Convert to rover coordinates


    X = z_cam

    # Image right = rover -Y
    Y = -x_cam

    # Image down = rover -Z
    Z = (
        CAMERA_TO_NOZZLE_Z
        - y_cam
    )

    return X, Y, Z



# DICTIONARY VERSION


def camera_pixel_to_xyz_dict(
    pixel_x,
    pixel_y,
    distance_mm
):
    """
    Same conversion as camera_pixel_to_xyz(),
    but returns a dictionary.
    """

    X, Y, Z = camera_pixel_to_xyz(
        pixel_x,
        pixel_y,
        distance_mm
    )

    return {
        "x": float(X),
        "y": float(Y),
        "z": float(Z)
    }



# OPTIONAL STANDALONE TEST


if __name__ == "__main__":

    print()
    print("=" * 50)
    print("CAMERA → XYZ MODULE TEST")
    print("=" * 50)

    tests = [
        (318, 236, 150),
        (322, 238, 150),
        (510, 390, 200)
    ]

    for pixel_x, pixel_y, distance in tests:

        xyz = camera_pixel_to_xyz(
            pixel_x,
            pixel_y,
            distance
        )

        print()
        print(
            f"Pixel: ({pixel_x}, {pixel_y})"
        )

        print(
            f"Distance: {distance} mm"
        )

        print(
            f"X = {xyz[0]:.2f} mm"
        )

        print(
            f"Y = {xyz[1]:.2f} mm"
        )

        print(
            f"Z = {xyz[2]:.2f} mm"
        )

    print()
    print("=" * 50)
