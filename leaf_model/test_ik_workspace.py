from inverse_kinematics import forward_kinematics, inverse_kinematics

poses = [
    (45, 90, 75),   # HOME
    (45, 85, 75),   # shoulder slightly down
    (45, 80, 75),   # shoulder down
    (60, 80, 60),   # base + shoulder + elbow
    (30, 80, 60),   # opposite base direction
]

print("=" * 60)
print("KNOWN-REACHABLE IK TEST")
print("=" * 60)

for base, shoulder, elbow in poses:

    x, y, z = forward_kinematics(
        base, shoulder, elbow
    )


    print(
        f"Original Servo Pose:"
        f" Base={base}°"
        f" Shoulder={shoulder}°"
        f" Elbow={elbow}°"
    )

    print(
        f"Generated XYZ:"
        f" X={x:.2f} mm"
        f" Y={y:.2f} mm"
        f" Z={z:.2f} mm"
    )

    try:

        b, s, e = inverse_kinematics(x, y, z)

        print(
            f"IK Result:"
            f" Base={b:.2f}°"
            f" Shoulder={s:.2f}°"
            f" Elbow={e:.2f}°"
        )

        error = (
            abs(b - base)
            + abs(s - shoulder)
            + abs(e - elbow)
        )

        if error < 1.0:
            print("RESULT: PASS")

        else:
            print(f"RESULT: CHECK - error={error:.2f}°")

    except ValueError as err:
        print("RESULT: FAIL")
        print(err)

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
