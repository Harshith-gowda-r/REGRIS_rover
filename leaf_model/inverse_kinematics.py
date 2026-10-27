import math



# ARM GEOMETRY


BASE_HEIGHT = 55.0
BASE_TO_SHOULDER = 30.0

L1 = 120.0
L2 = 90.0

SHOULDER_HEIGHT = BASE_HEIGHT + BASE_TO_SHOULDER



# SERVO LIMITS


BASE_MIN = 0.0
BASE_MAX = 90.0

SHOULDER_MIN = 0.0
SHOULDER_MAX = 90.0

ELBOW_MIN = 0.0
ELBOW_MAX = 90.0



# HOME POSITION


BASE_HOME = 45.0
SHOULDER_HOME = 90.0
ELBOW_HOME = 75.0



# FORWARD KINEMATICS


def forward_kinematics(
    base_servo,
    shoulder_servo,
    elbow_servo
):

    phi = math.radians(
        base_servo - BASE_HOME
    )

    q1 = math.radians(
        shoulder_servo - SHOULDER_HOME
    )

    q2 = math.radians(
        elbow_servo - ELBOW_HOME
    )

    r = (
        L1 * math.cos(q1)
        +
        L2 * math.cos(q1 + q2)
    )

    z = (
        SHOULDER_HEIGHT
        +
        L1 * math.sin(q1)
        +
        L2 * math.sin(q1 + q2)
    )

    x = r * math.cos(phi)
    y = r * math.sin(phi)

    return x, y, z



# DISTANCE BETWEEN TWO XYZ POINTS


def xyz_distance(
    target,
    actual
):

    dx = actual[0] - target[0]
    dy = actual[1] - target[1]
    dz = actual[2] - target[2]

    return math.sqrt(
        dx * dx +
        dy * dy +
        dz * dz
    )



# NEAREST REACHABLE POINT


def inverse_kinematics(
    x,
    y,
    z,
    max_adjustment_mm=70.0
):
    """
    Find the closest physically reachable servo position.

    IMPORTANT:
    Servo limits remain strictly 0-90 degrees.

    The function first tries to find the exact target.
    If the exact target cannot be reached, it searches
    the valid servo workspace and returns the closest
    reachable position.

    Returns:
        (base, shoulder, elbow)

    Raises:
        ValueError only when the closest reachable point
        is farther than max_adjustment_mm.
    """

    target = (
        float(x),
        float(y),
        float(z)
    )


    # STEP 1
    # Determine the best base angle.
    #
    # From the FK model:
    #
    # phi = base - BASE_HOME
    #
    # Therefore:
    #
    # base = atan2(y,x) + BASE_HOME


    phi_deg = math.degrees(
        math.atan2(y, x)
    )

    desired_base = (
        phi_deg + BASE_HOME
    )

    desired_base = max(
        BASE_MIN,
        min(BASE_MAX, desired_base)
    )


    # STEP 2
    # Coarse search
    #
    # Search the complete physical servo range.
    #
    # This means the FK model itself determines
    # what is reachable.


    best_error = float("inf")
    best_solution = None

    # 2-degree coarse search
    coarse_step = 2.0

    # Search base around the desired direction.
    #
    # Include the complete range so that this function
    # remains safe even when the target direction is
    # outside the base's 0-90 degree range.
    base_values = [
        BASE_MIN + i * coarse_step
        for i in range(
            int(
                (BASE_MAX - BASE_MIN)
                / coarse_step
            ) + 1
        )
    ]

    shoulder_values = [
        SHOULDER_MIN + i * coarse_step
        for i in range(
            int(
                (SHOULDER_MAX - SHOULDER_MIN)
                / coarse_step
            ) + 1
        )
    ]

    elbow_values = [
        ELBOW_MIN + i * coarse_step
        for i in range(
            int(
                (ELBOW_MAX - ELBOW_MIN)
                / coarse_step
            ) + 1
        )
    ]

    for base in base_values:

        # Small optimization:
        # don't waste the entire search on base angles
        # far from the requested direction.
        base_direction_error = abs(
            base - desired_base
        )

        if (
            base_direction_error > 45.0
            and
            desired_base >= BASE_MIN
            and
            desired_base <= BASE_MAX
        ):
            continue

        for shoulder in shoulder_values:

            for elbow in elbow_values:

                actual = forward_kinematics(
                    base,
                    shoulder,
                    elbow
                )

                error = xyz_distance(
                    target,
                    actual
                )

                if error < best_error:

                    best_error = error

                    best_solution = (
                        base,
                        shoulder,
                        elbow
                    )


    # STEP 3
    # Fine search around the best coarse solution.


    if best_solution is None:

        raise ValueError(
            "No valid servo solution found."
        )

    coarse_base, coarse_shoulder, coarse_elbow = (
        best_solution
    )

    fine_range = 2.5
    fine_step = 0.25

    base_start = max(
        BASE_MIN,
        coarse_base - fine_range
    )

    base_end = min(
        BASE_MAX,
        coarse_base + fine_range
    )

    shoulder_start = max(
        SHOULDER_MIN,
        coarse_shoulder - fine_range
    )

    shoulder_end = min(
        SHOULDER_MAX,
        coarse_shoulder + fine_range
    )

    elbow_start = max(
        ELBOW_MIN,
        coarse_elbow - fine_range
    )

    elbow_end = min(
        ELBOW_MAX,
        coarse_elbow + fine_range
    )

    base = base_start

    while base <= base_end + 0.001:

        shoulder = shoulder_start

        while shoulder <= shoulder_end + 0.001:

            elbow = elbow_start

            while elbow <= elbow_end + 0.001:

                actual = forward_kinematics(
                    base,
                    shoulder,
                    elbow
                )

                error = xyz_distance(
                    target,
                    actual
                )

                if error < best_error:

                    best_error = error

                    best_solution = (
                        base,
                        shoulder,
                        elbow
                    )

                elbow += fine_step

            shoulder += fine_step

        base += fine_step


    # STEP 4
    # Check whether the nearest reachable position
    # is reasonably close to the requested position.


    if best_error > max_adjustment_mm:

        raise ValueError(
            "Target is outside the usable workspace. "
            f"Nearest reachable position is "
            f"{best_error:.1f} mm away."
        )


    # STEP 5
    # Return the nearest valid servo position.


    return best_solution



# DETAILED IK RESULT


def inverse_kinematics_detailed(
    x,
    y,
    z,
    max_adjustment_mm=70.0
):
    """
    Same IK as inverse_kinematics(), but returns
    additional information useful for debugging.
    """

    servo = inverse_kinematics(
        x,
        y,
        z,
        max_adjustment_mm
    )

    base, shoulder, elbow = servo

    actual_xyz = forward_kinematics(
        base,
        shoulder,
        elbow
    )

    error = xyz_distance(
        (x, y, z),
        actual_xyz
    )

    return {
        "requested_xyz": {
            "x": float(x),
            "y": float(y),
            "z": float(z)
        },

        "servo_angles": {
            "base": round(base, 2),
            "shoulder": round(shoulder, 2),
            "elbow": round(elbow, 2)
        },

        "reachable_xyz": {
            "x": round(actual_xyz[0], 2),
            "y": round(actual_xyz[1], 2),
            "z": round(actual_xyz[2], 2)
        },

        "adjustment_mm": round(error, 2)
    }



# VALIDATION


def test_pose(
    base,
    shoulder,
    elbow
):

    print("--------------------------------------------")

    print(
        f"Servo angles: "
        f"Base={base}° "
        f"Shoulder={shoulder}° "
        f"Elbow={elbow}°"
    )

    actual = forward_kinematics(
        base,
        shoulder,
        elbow
    )

    print("\nForward Kinematics:")

    print(
        f"X = {actual[0]:.2f} mm"
    )

    print(
        f"Y = {actual[1]:.2f} mm"
    )

    print(
        f"Z = {actual[2]:.2f} mm"
    )

    try:

        result = inverse_kinematics_detailed(
            *actual,
            max_adjustment_mm=70
        )

        print("\nInverse Kinematics:")

        print(
            f"Base     = "
            f"{result['servo_angles']['base']:.2f}°"
        )

        print(
            f"Shoulder = "
            f"{result['servo_angles']['shoulder']:.2f}°"
        )

        print(
            f"Elbow    = "
            f"{result['servo_angles']['elbow']:.2f}°"
        )

        print(
            f"Adjustment = "
            f"{result['adjustment_mm']:.2f} mm"
        )

    except ValueError as error:

        print("\nIK ERROR:")
        print(error)



# MAIN TEST


if __name__ == "__main__":

    print("=" * 60)
    print("       ARM NUMERICAL IK VALIDATION")
    print("=" * 60)

    print("\nTEST 1: HOME")

    test_pose(
        45,
        90,
        75
    )

    print("\nTEST 2")

    test_pose(
        45,
        85,
        75
    )

    print("\nTEST 3")

    test_pose(
        45,
        80,
        75
    )

    print("\nTEST 4")

    test_pose(
        60,
        80,
        60
    )

    print("\nTEST 5")

    test_pose(
        30,
        80,
        60
    )

    print("\n" + "=" * 60)
    print("VALIDATION COMPLETE")
    print("=" * 60)
