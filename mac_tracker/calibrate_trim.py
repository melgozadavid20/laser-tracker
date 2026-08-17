"""
Live aim-offset calibration - runs the real pursuit tracking, but instead of
targeting true frame-center it targets an adjustable pixel offset
(AIM_OFFSET_X/Y). Jog that target with arrow keys/WASD while pursuit
continuously re-converges to it, and watch the actual laser dot until it
lands on your hand.

This is different from (and replaces) an earlier, broken approach that tried
to add a correction AFTER pursuit computed its target - that fought itself,
since pursuit's whole job is re-centering the hand and would just cancel any
after-the-fact nudge back out. Moving the TARGET instead is stable: pursuit
converges to holding your hand at that off-center frame position, which is
exactly where the physically-offset laser lands on it.

Just hold your hand naturally in view - pursuit does the centering/tracking
automatically. Watch the laser, not the screen, while jogging.

Setup: standard hardware startup - TalentCell on, then Pico USB in, wait for
the ramp to center. Then run this script.

Controls (click into the window first):
  Arrow keys / WASD  - jog the aim-offset target 5 pixels at a time
  SPACE              - print the current aim-offset values (without quitting)
  Q / Esc            - quit and print final values (recenters safely)
"""
import cv2
import time

try:
    import mediapipe as mp
except ImportError:
    raise SystemExit("mediapipe not installed - use venv312: source ../venv312/bin/activate")

from pico_serial import connect, send_angles
from tracker_main import (
    PICO_PORT, CAMERA_INDEX, CENTER_ANGLE, SMOOTHING,
    compute_tracking_target, mp_hands, mp_draw,
)

OFFSET_STEP = 5  # pixels per keypress

def main():
    ser = connect(PICO_PORT)
    print(f"Connected to {PICO_PORT}")
    send_angles(ser, CENTER_ANGLE, CENTER_ANGLE)
    time.sleep(1)

    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print(f"Error: could not open camera at index {CAMERA_INDEX}.")
        ser.close()
        return

    smoothed_pan = float(CENTER_ANGLE)
    smoothed_tilt = float(CENTER_ANGLE)
    aim_offset_x = 0
    aim_offset_y = 0

    print("\nHold your hand naturally in view - pursuit tracks/centers it automatically.")
    print("Watch the LASER (not the screen) and jog the target with arrows/WASD until")
    print("the laser lands on your hand. SPACE to print current values, Q to quit.\n")

    try:
        with mp_hands.Hands(
            model_complexity=0,
            max_num_hands=1,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.5,
        ) as hands:
            while True:
                ret, frame = cap.read()
                if not ret:
                    continue
                frame_h, frame_w = frame.shape[:2]

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = hands.process(rgb)

                if results.multi_hand_landmarks:
                    hand_landmarks = results.multi_hand_landmarks[0]
                    palm = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP]
                    cx, cy = int(palm.x * frame_w), int(palm.y * frame_h)
                    target_pan, target_tilt, _ = compute_tracking_target(
                        frame, cx, cy, smoothed_pan, smoothed_tilt,
                        aim_offset_x=aim_offset_x, aim_offset_y=aim_offset_y,
                    )
                    mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                    cv2.circle(frame, (cx, cy), 8, (255, 0, 0), -1)
                else:
                    target_pan, target_tilt = smoothed_pan, smoothed_tilt

                smoothed_pan += SMOOTHING * (target_pan - smoothed_pan)
                smoothed_tilt += SMOOTHING * (target_tilt - smoothed_tilt)
                pan_angle = int(round(smoothed_pan))
                tilt_angle = int(round(smoothed_tilt))
                send_angles(ser, pan_angle, tilt_angle)

                # Draw a crosshair at the current aim-offset target so you can see
                # where pursuit is trying to hold your hand.
                marker_x = frame_w // 2 + aim_offset_x
                marker_y = frame_h // 2 + aim_offset_y
                cv2.drawMarker(frame, (marker_x, marker_y), (0, 165, 255),
                                markerType=cv2.MARKER_CROSS, markerSize=20, thickness=2)

                cv2.putText(frame, f"AIM_OFFSET_X={aim_offset_x}  AIM_OFFSET_Y={aim_offset_y}",
                            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.putText(frame, "arrows/WASD=jog target, SPACE=print, Q=quit",
                            (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
                cv2.imshow("Aim Offset Calibration", frame)

                key = cv2.waitKeyEx(1)
                if key in (81, 2424832, 63234, ord('a'), ord('A')):
                    aim_offset_x -= OFFSET_STEP
                elif key in (83, 2555904, 63235, ord('d'), ord('D')):
                    aim_offset_x += OFFSET_STEP
                elif key in (82, 2490368, 63232, ord('w'), ord('W')):
                    aim_offset_y -= OFFSET_STEP
                elif key in (84, 2621440, 63233, ord('s'), ord('S')):
                    aim_offset_y += OFFSET_STEP
                elif key == 32:  # SPACE
                    print(f"  Current: AIM_OFFSET_X={aim_offset_x}  AIM_OFFSET_Y={aim_offset_y}")
                elif key in (ord('q'), ord('Q'), 27):
                    break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print(f"\nFinal: AIM_OFFSET_X = {aim_offset_x}   AIM_OFFSET_Y = {aim_offset_y}")
        print("Tell me these numbers and I'll update tracker_main.py.")
        send_angles(ser, CENTER_ANGLE, CENTER_ANGLE)
        ser.close()

if __name__ == "__main__":
    main()
