"""
Calibration tool for PAN_AIM_CENTER/TILT_AIM_CENTER + GAIN_X/GAIN_Y.

Measures two separate things tracker_main.py needs:
  1. AIM CENTER (the bias/offset fix) - the actual angle that points the
     laser at whatever the camera's optical center is looking at. The
     mount's mechanical 90/90 "home" has no guarantee of lining up with
     where the camera looks - they're two independently-mounted things. If
     they don't match, the laser will always be offset from the hand by a
     fixed amount, no matter how good the gain is. This is captured FIRST,
     as a CENTER point, before anything else.
  2. GAIN (the scale fix) - how many degrees per pixel of offset from that
     center. Measured the same way as before: hold your hand left/right/up/
     down, jog the laser onto it, capture.

For each of the 5 points (center, left, right, up, down), you jog the
servos with arrow keys/WASD (1 degree at a time, for precision) until the
laser dot visually lands on your hand, then press SPACE to capture. After
all five, it computes and prints the real PAN_AIM_CENTER/TILT_AIM_CENTER and
GAIN_X/GAIN_Y to use.

Both depend on your camera/mount physical setup and distance, so a value
that felt fine at one distance/setup won't be exactly right at another -
recalibrate any time you move the camera, mount, or typical distance.

Setup: same as any other test - TalentCell on, then Pico USB in, so it boots
centered. Then run this script.

Controls (click into the window first):
  Arrow keys / WASD  - jog the mount 1 degree at a time
  SPACE              - capture a calibration point at the current hand position
  Q / Esc            - quit early (recenters and disconnects safely)
"""
import cv2
import time

try:
    import mediapipe as mp
except ImportError:
    raise SystemExit(
        "mediapipe is not installed, or your Python version isn't supported.\n"
        "Use the venv312 environment: source ../venv312/bin/activate\n"
    )

from pico_serial import connect, send_angles

PICO_PORT = "/dev/tty.usbmodem14201"
CENTER_ANGLE = 90
STEP = 1  # fine 1-degree jog for precise calibration, unlike manual_control.py's 5

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

def main():
    ser = connect(PICO_PORT)
    print(f"Connected to {PICO_PORT}")
    send_angles(ser, CENTER_ANGLE, CENTER_ANGLE)
    time.sleep(1)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: could not open webcam.")
        ser.close()
        return

    pan = CENTER_ANGLE
    tilt = CENTER_ANGLE

    # CENTER goes first - it's the aim-center/bias fix, and the left/right/up/
    # down gain points are measured relative to it (not to a hardcoded 90).
    # Order alternates sides afterward so you're not holding your arm at one
    # extreme for too long while jogging the other points.
    points = [
        ("CENTER", "Hold your hand at the CENTER of frame"),
        ("LEFT",  "Hold your hand to the LEFT side of frame"),
        ("RIGHT", "Hold your hand to the RIGHT side of frame"),
        ("UP",    "Hold your hand toward the TOP of frame"),
        ("DOWN",  "Hold your hand toward the BOTTOM of frame"),
    ]
    captured = {}

    print("\nFor each position: move your hand there, use arrows/WASD to jog the")
    print("laser onto your hand, then press SPACE to capture. Q to quit early.")
    print("Try to stay roughly the same distance from the camera for every point.\n")

    try:
        with mp_hands.Hands(
            model_complexity=0,
            max_num_hands=1,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.5,
        ) as hands:
            point_idx = 0
            while point_idx < len(points):
                label, instruction = points[point_idx]

                ret, frame = cap.read()
                if not ret:
                    continue
                frame_h, frame_w = frame.shape[:2]

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = hands.process(rgb)

                offset_x = offset_y = None
                if results.multi_hand_landmarks:
                    hand_landmarks = results.multi_hand_landmarks[0]
                    palm = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP]
                    cx, cy = int(palm.x * frame_w), int(palm.y * frame_h)
                    offset_x = cx - frame_w // 2
                    offset_y = cy - frame_h // 2
                    mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                    cv2.circle(frame, (cx, cy), 8, (255, 0, 0), -1)

                cv2.putText(frame, f"Point {point_idx+1}/{len(points)}: {instruction}",
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                cv2.putText(frame, f"PAN={pan} TILT={tilt}  (arrows/WASD jog, SPACE=capture)",
                            (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
                if offset_x is not None:
                    cv2.putText(frame, f"hand offset: x={offset_x} y={offset_y}",
                                (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 1)
                else:
                    cv2.putText(frame, "hand not detected", (10, 90),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 1)

                cv2.imshow("Gain Calibration", frame)
                key = cv2.waitKeyEx(1)

                if key in (81, 2424832, 63234, ord('a'), ord('A')):
                    pan = max(0, pan - STEP); send_angles(ser, pan, tilt)
                elif key in (83, 2555904, 63235, ord('d'), ord('D')):
                    pan = min(180, pan + STEP); send_angles(ser, pan, tilt)
                elif key in (82, 2490368, 63232, ord('w'), ord('W')):
                    tilt = max(0, tilt - STEP); send_angles(ser, pan, tilt)
                elif key in (84, 2621440, 63233, ord('s'), ord('S')):
                    tilt = min(180, tilt + STEP); send_angles(ser, pan, tilt)
                elif key == 32:  # SPACE
                    if offset_x is None:
                        print("  No hand detected - can't capture, try again.")
                    else:
                        captured[label] = (offset_x, offset_y, pan, tilt)
                        print(f"  Captured {label}: offset=({offset_x},{offset_y}) angle=(pan={pan},tilt={tilt})")
                        point_idx += 1
                elif key in (ord('q'), ord('Q'), 27):
                    print("Quit early.")
                    break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("\nRecentering and closing...")
        send_angles(ser, CENTER_ANGLE, CENTER_ANGLE)
        ser.close()

    if "CENTER" not in captured:
        print("CENTER point wasn't captured - can't compute anything without it.")
        return

    center_ox, center_oy, center_pan, center_tilt = captured["CENTER"]
    print("\n--- Results ---")
    print(f"Recommended PAN_AIM_CENTER = {center_pan}")
    print(f"Recommended TILT_AIM_CENTER = {center_tilt}")
    if center_ox != 0 or center_oy != 0:
        print(f"  (note: hand offset wasn't exactly 0 at capture - was ({center_ox},{center_oy}), "
              f"close enough is fine)")

    gain_x_samples = []
    gain_y_samples = []
    for key_label in ("LEFT", "RIGHT"):
        if key_label in captured:
            ox, oy, p, t = captured[key_label]
            if ox != 0:
                gain_x_samples.append(abs((p - center_pan) / ox))
    for key_label in ("UP", "DOWN"):
        if key_label in captured:
            ox, oy, p, t = captured[key_label]
            if oy != 0:
                gain_y_samples.append(abs((t - center_tilt) / oy))

    if gain_x_samples:
        gain_x = sum(gain_x_samples) / len(gain_x_samples)
        print(f"Recommended GAIN_X = {gain_x:.4f}  (samples: {[round(g, 4) for g in gain_x_samples]})")
    else:
        print("No usable PAN samples captured.")

    if gain_y_samples:
        gain_y = sum(gain_y_samples) / len(gain_y_samples)
        print(f"Recommended GAIN_Y = {gain_y:.4f}  (samples: {[round(g, 4) for g in gain_y_samples]})")
    else:
        print("No usable TILT samples captured.")

    print("\nTell me these numbers and I'll update tracker_main.py.")

if __name__ == "__main__":
    main()
