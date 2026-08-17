import cv2
import time

try:
    import mediapipe as mp
except ImportError:
    raise SystemExit(
        "mediapipe is not installed, or your Python version isn't supported.\n"
        "mediapipe currently supports Python 3.9-3.12 only (not 3.13/3.14), so if your\n"
        "venv is on a newer Python you'll need a separate venv with e.g. Python 3.12:\n"
        "    python3.12 -m venv venv312 && source venv312/bin/activate\n"
        "    pip install mediapipe opencv-python pyserial\n"
    )

from pico_serial import connect, send_angles

# Serial port for the Pico - update once hardware is connected
# find it via `ls /dev/tty.*` with the Pico plugged in
PICO_PORT = "/dev/tty.usbmodem14201"

# CENTER_ANGLE is the mechanical "home" position (used for the startup ramp,
# lost-hand repositioning, idle, and safety recenter-on-exit) - it just needs
# to be a safe resting position, nothing more.
CENTER_ANGLE = 90

# Camera device index - the small ELP camera mounted on the bracket (found via
# find_camera.py). This is DIFFERENT from the old setup: the camera now moves
# WITH the laser instead of sitting stationary, so the whole open-loop
# GAIN_X/GAIN_Y + PAN_AIM_CENTER/TILT_AIM_CENTER calibration is gone - it's no
# longer needed. Since the camera and laser are rigidly mounted together and
# point the same direction, "hand centered in frame" now directly means "laser
# roughly on hand" by construction. Tracking below just continuously nudges
# toward keeping the hand centered (pursuit), rather than computing an
# absolute target angle from a calibrated mapping.
CAMERA_INDEX = 0

# How long to show the "initializing/centering" screen before tracking starts.
# There's no feedback sensor, so this is just a fixed settle time (not a true
# confirmation the mount reached center) - but it stops you from moving your
# hand before the servos have caught up, and gives a clear on-screen cue for
# when it's actually safe to start.
INIT_SECONDS = 1.5
READY_FLASH_SECONDS = 0.8

# If the laser moves the WRONG direction relative to your hand (e.g. hand moves
# right, laser goes left) once everything's running, flip the matching flag below
# instead of touching the math - this depends on how the camera/bracket ended up
# physically oriented relative to each other. IMPORTANT: these will likely need
# to be re-checked now that the camera moved onto the bracket - the physical
# relationship between "servo turns this way" and "co-mounted camera's view
# shifts that way" isn't guaranteed to match the old stationary-camera setup.
# Test slowly at first.
INVERT_PAN = False
INVERT_TILT = True

# Every video frame gives a slightly noisy landmark position (even for a "still"
# hand), and the tracker sends a new target ~15-30x/sec - too fast for the servo
# to ever finish a move before getting redirected. SMOOTHING blends each new
# target into a running value instead of jumping straight to it, which is what
# turns that jitter into smooth motion.
# 1.0 = no smoothing (raw/jumpy). Lower = smoother but laggier. 0.2-0.3 is a good start.
SMOOTHING = 0.4

# Pursuit gain: how many degrees to nudge per pixel that the hand is off-center.
# This is now the ONLY tracking gain (no more open-loop GAIN_X/GAIN_Y calibrated
# to a stationary camera) - since the camera moves with the laser, keeping the
# hand centered in frame IS the tracking goal, applied incrementally each frame
# on top of the current position rather than computed as an absolute target.
PURSUIT_GAIN_X = 0.045
PURSUIT_GAIN_Y = 0.045

# Safety cap: no matter how far off-center the hand is, pursuit can only nudge
# the angle by this many degrees per frame. A bad detection or a fast hand swipe
# can then only ever cause a bounded step you can see and correct, never a
# violent slam toward a mechanical limit.
PURSUIT_MAX_STEP = 4

# Aim offset (in pixels): the laser isn't physically at the exact same point
# as the camera lens (small mounting offset), so the frame position where the
# laser actually lands isn't necessarily dead-center - this is normal
# parallax, like a rifle scope mounted above the barrel. Rather than bolting a
# correction onto the servo angle AFTER pursuit decides where to aim (which
# fights itself - pursuit's whole job is re-centering the hand, so it just
# cancels any such correction back out), we instead tell pursuit to treat THIS
# pixel offset as its target instead of true center (0, 0). That's a stable
# goal: pursuit converges to holding the hand at this off-center frame
# position, which is exactly where the physically-offset laser lands on it.
# Measure with calibrate_trim.py.
AIM_OFFSET_X = 350   # measured via calibrate_trim.py
AIM_OFFSET_Y = -105  # measured via calibrate_trim.py

# --- Lost-hand behavior ---
# If the hand drops out of detection for a moment (motion blur, hand at the edge
# of frame, etc), don't just freeze - coast briefly in the direction it was last
# moving, capped for safety. If it stays lost longer than that, give up coasting
# and smoothly return to the center/home position instead of sitting wherever it
# happened to be.
LOST_GRACE_FRAMES = 8          # ~0.3-0.5s of coasting on a blip before we start worrying
REPOSITION_AFTER_FRAMES = 30   # ~1-2s lost before we give up and head home
MOMENTUM_MAX_STEP = 2          # safety cap on blind coasting, same idea as CLOSED_LOOP_MAX_STEP

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

def clamp(value, min_value=0, max_value=180):
    return max(min_value, min(max_value, value))

def compute_tracking_target(frame, cx, cy, smoothed_pan, smoothed_tilt,
                             aim_offset_x=None, aim_offset_y=None):
    """Given a detected hand position, work out where to aim and what to show.
    Returns (target_pan, target_tilt, status_text).

    Pursuit logic: the camera is mounted on the bracket right next to the
    laser, so frame-center (adjusted by aim_offset_x/y, see AIM_OFFSET_X/Y
    above) represents wherever the laser is currently pointed. We nudge
    incrementally toward keeping the hand at that target frame position,
    capped per-frame for safety, instead of computing an absolute angle from
    a calibrated open-loop mapping. aim_offset defaults to the module-level
    AIM_OFFSET_X/Y constants, but calibrate_trim.py passes its own live
    values in while you jog them."""
    if aim_offset_x is None:
        aim_offset_x = AIM_OFFSET_X
    if aim_offset_y is None:
        aim_offset_y = AIM_OFFSET_Y

    frame_h, frame_w = frame.shape[:2]
    offset_x = (cx - frame_w // 2) - aim_offset_x
    offset_y = (cy - frame_h // 2) - aim_offset_y

    pan_dir = 1 if INVERT_PAN else -1
    tilt_dir = 1 if INVERT_TILT else -1
    pan_step = clamp(pan_dir * offset_x * PURSUIT_GAIN_X, -PURSUIT_MAX_STEP, PURSUIT_MAX_STEP)
    tilt_step = clamp(tilt_dir * offset_y * PURSUIT_GAIN_Y, -PURSUIT_MAX_STEP, PURSUIT_MAX_STEP)
    target_pan = clamp(smoothed_pan + pan_step)
    target_tilt = clamp(smoothed_tilt + tilt_step)
    return target_pan, target_tilt, "TRACKING"

def main():
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print(f"Error: Could not open webcam at index {CAMERA_INDEX}. "
              f"Run find_camera.py to check the current index.")
        return

    ser = None
    try:
        ser = connect(PICO_PORT)
        print(f"Connected to Pico on {PICO_PORT}")
        # The Pico ramps to center itself at boot (as long as the TalentCell
        # was powered on BEFORE the Pico booted/reset - see
        # pico_firmware/main.py). It should already be centered by the time
        # we connect, so this just confirms/holds that position.
        send_angles(ser, CENTER_ANGLE, CENTER_ANGLE)
    except Exception as e:
        print(f"Warning: Could not connect to Pico ({e}). Running in vision-only mode.")

    # Running smoothed angle, carried across frames. Starts centered.
    smoothed_pan = float(CENTER_ANGLE)
    smoothed_tilt = float(CENTER_ANGLE)

    # State for the lost-hand behavior: how many consecutive frames we've gone
    # without a detection, the last known-good target (for coasting), and the
    # estimated per-frame velocity of that target (for "keep moving the way it
    # was going" instead of just freezing in place).
    lost_count = 0
    prev_target_pan = float(CENTER_ANGLE)
    prev_target_tilt = float(CENTER_ANGLE)
    pan_velocity = 0.0
    tilt_velocity = 0.0

    # Everything from here down is wrapped in try/finally: the Pico holds whatever
    # angle it was last told, indefinitely, even after this script stops running -
    # it has no idea the host quit. Without this, stopping the script (even via
    # Ctrl-C) while a servo is stalled against a limit leaves it stalled there,
    # straining, until you physically cut power. The finally block guarantees we
    # always send one last "recenter" command before closing, no matter how this
    # loop exits (normal 'q' quit, Ctrl-C, or a crash).
    try:
        # max_num_hands=1 keeps us locked onto a single hand (avoids the laser jumping
        # between hands if more than one is in frame). model_complexity=0 is the fastest
        # model variant, which matters for keeping this a real-time loop.
        with mp_hands.Hands(
            model_complexity=0,
            max_num_hands=1,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.5,
        ) as hands:
            # Show a clear "initializing" screen while the mount settles at
            # center, then a brief "ready" flash, before any hand tracking
            # starts - so you're never guessing whether it's safe to move yet.
            quit_during_init = False
            init_start = time.time()
            while time.time() - init_start < INIT_SECONDS:
                ret, frame = cap.read()
                if not ret:
                    continue
                cv2.putText(frame, "Initializing - centering mount...", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 165, 255), 2)
                cv2.imshow("Laser Tracker", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    quit_during_init = True
                    break

            ready_start = time.time()
            while not quit_during_init and time.time() - ready_start < READY_FLASH_SECONDS:
                ret, frame = cap.read()
                if not ret:
                    continue
                cv2.putText(frame, "CENTERED - ready! Move your hand", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.imshow("Laser Tracker", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    quit_during_init = True
                    break

            while not quit_during_init:
                ret, frame = cap.read()
                if not ret:
                    continue

                frame_h, frame_w = frame.shape[:2]

                # MediaPipe expects RGB input; OpenCV captures frames as BGR
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = hands.process(rgb)

                if results.multi_hand_landmarks:
                    hand_landmarks = results.multi_hand_landmarks[0]  # only tracking one hand

                    # Track the middle-finger MCP joint (landmark 9) as the hand's "center".
                    # It sits roughly in the middle of the palm and is much steadier frame-to-frame
                    # than a fingertip or the wrist, which both swing more during motion.
                    palm = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_MCP]
                    cx, cy = int(palm.x * frame_w), int(palm.y * frame_h)

                    target_pan, target_tilt, status = compute_tracking_target(
                        frame, cx, cy, smoothed_pan, smoothed_tilt
                    )

                    # Update velocity estimate and reset the lost-hand counter now
                    # that we have a fresh detection.
                    pan_velocity = target_pan - prev_target_pan
                    tilt_velocity = target_tilt - prev_target_tilt
                    prev_target_pan, prev_target_tilt = target_pan, target_tilt
                    lost_count = 0

                    mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                    cv2.circle(frame, (cx, cy), 8, (255, 0, 0), -1)

                else:
                    lost_count += 1

                    if lost_count <= LOST_GRACE_FRAMES:
                        # Brief dropout - keep coasting in the direction it was last
                        # heading, capped so a bad velocity estimate can't run away.
                        step_pan = clamp(pan_velocity, -MOMENTUM_MAX_STEP, MOMENTUM_MAX_STEP)
                        step_tilt = clamp(tilt_velocity, -MOMENTUM_MAX_STEP, MOMENTUM_MAX_STEP)
                        prev_target_pan = clamp(prev_target_pan + step_pan)
                        prev_target_tilt = clamp(prev_target_tilt + step_tilt)
                        target_pan, target_tilt = prev_target_pan, prev_target_tilt
                        status = "SEARCHING (coasting)"
                    elif abs(smoothed_pan - CENTER_ANGLE) < 1 and abs(smoothed_tilt - CENTER_ANGLE) < 1:
                        # Already home and still no hand - just idle here.
                        target_pan, target_tilt = float(CENTER_ANGLE), float(CENTER_ANGLE)
                        prev_target_pan, prev_target_tilt = target_pan, target_tilt
                        pan_velocity = tilt_velocity = 0.0
                        status = "IDLE (no hand detected)"
                    else:
                        # Lost too long - give up and head back to home position.
                        target_pan, target_tilt = float(CENTER_ANGLE), float(CENTER_ANGLE)
                        prev_target_pan, prev_target_tilt = target_pan, target_tilt
                        pan_velocity = tilt_velocity = 0.0
                        status = "REPOSITIONING (lost - returning home)"

                # Blend toward the new target instead of jumping straight to it -
                # this is what removes the frame-to-frame jitter/stutter. Runs every
                # frame regardless of detection, so motion stays fluid instead of
                # freezing the instant a detection is missed.
                smoothed_pan += SMOOTHING * (target_pan - smoothed_pan)
                smoothed_tilt += SMOOTHING * (target_tilt - smoothed_tilt)
                pan_angle = int(round(smoothed_pan))
                tilt_angle = int(round(smoothed_tilt))

                status_color = (0, 255, 0) if status.startswith("TRACKING") else (0, 165, 255)
                cv2.putText(frame, f"Pan: {pan_angle} Tilt: {tilt_angle}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.putText(frame, status, (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)

                # Always print - handy for watching the numbers/state live.
                print(f"Pan: {pan_angle}, Tilt: {tilt_angle} | {status} | raw target: {target_pan}, {target_tilt}")
                if ser is not None:
                    send_angles(ser, pan_angle, tilt_angle)

                cv2.imshow("Laser Tracker", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
    finally:
        cap.release()
        cv2.destroyAllWindows()
        if ser is not None:
            try:
                print("Recentering servos before exit...")
                send_angles(ser, CENTER_ANGLE, CENTER_ANGLE)
            except Exception:
                pass
            ser.close()

if __name__ == "__main__":
    main()
