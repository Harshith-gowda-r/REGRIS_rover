from inverse_kinematics import forward_kinematics, inverse_kinematics

print()

print("REAL ARM WORKSPACE TEST")

print()

# Test every 5 degrees within the actual servo limits
reachable = []

for base in range(0, 91, 5):
    for shoulder in range(0, 91, 5):
        for elbow in range(0, 91, 5):

            x, y, z = forward_kinematics(
                base,
                shoulder,
                elbow
            )

            try:
                b, s, e = inverse_kinematics(x, y, z)

                reachable.append((x, y, z))

            except ValueError:
                pass


print(f"Reachable configurations tested: {len(reachable)}")
print()

xs = [p[0] for p in reachable]
ys = [p[1] for p in reachable]
zs = [p[2] for p in reachable]

print("REACHABLE WORKSPACE RANGE")

print(f"X minimum = {min(xs):.2f} mm")
print(f"X maximum = {max(xs):.2f} mm")
print(f"Y minimum = {min(ys):.2f} mm")
print(f"Y maximum = {max(ys):.2f} mm")
print(f"Z minimum = {min(zs):.2f} mm")
print(f"Z maximum = {max(zs):.2f} mm")


print()
print("KNOWN POSITIONS")


tests = [
    ("Home", 45, 90, 75),
    ("Test 2", 45, 85, 75),
    ("Test 3", 45, 80, 75),
    ("Test 4", 60, 80, 60),
    ("Test 5", 30, 80, 60),
]

for name, b, s, e in tests:

    x, y, z = forward_kinematics(b, s, e)

    print()
    print(name)
    print(f"Servo: {b}°, {s}°, {e}°")
    print(f"XYZ: ({x:.2f}, {y:.2f}, {z:.2f})")

    try:
        result = inverse_kinematics(x, y, z)
        print("IK: VALID")
        print(
            f"IK angles: "
            f"{result[0]:.2f}°, "
            f"{result[1]:.2f}°, "
            f"{result[2]:.2f}°"
        )

    except ValueError as error:
        print("IK: INVALID")
        print(error)

print()

