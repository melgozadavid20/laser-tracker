import cv2

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
PICO_PORT = "/dev/tty.usbmodem14101"

# Pan/tilt center + gain (degrees per pixel offset) - placeholder, tune once hardware is mounted
CENTER_ANGLE = 90
GAIN_X = 0.05
GAIN_Y = 0.05

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

def clamp(value, min_value=0, max_value=180):
    return max(min_value, min(max_value, value))

def offset_to_angles(offset_x, offset_y):
    pan_angle = clamp(CENTER_ANGLE - offset_x * GAIN_X)
    tilt_angle = clamp(CENTER_ANGLE - offset_y * GAIN_Y)
    return int(pan_angle), int(tilt_angle)

def main():
    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    ser = None
    try:
        ser = connect(PICO_PORT)
        print(f"Connected to Pico on {PICO_PORT}")
    except Exception as e:
        print(f"Warning: Could not connect to Pico ({e}). Running in vision-only mode.")

    # max_num_hands=1 keeps us locked onto a single hand (avoids the laser jumping
    # between hands if more than one is in frame). model_complexity=0 is the fastest
    # model variant, which matters for keeping this a real-time loop.
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

                offset_x = cx - frame_w // 2
                offset_y = cy - frame_h // 2

                pan_angle, tilt_angle = offset_to_angles(offset_x, offset_y)

                mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                cv2.circle(frame, (cx, cy), 8, (255, 0, 0), -1)
                cv2.putText(frame, f"Pan: {pan_angle} Tilt: {tilt_angle}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

                if ser is not None:
                    send_angles(ser, pan_angle, tilt_angle)
                else:
                    print(f"Pan: {pan_angle}, Tilt: {tilt_angle}")

            cv2.imshow("Laser Tracker", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cap.release()
    cv2.destroyAllWindows()
    if ser is not None:
        ser.close()

if __name__ == "__main__":
    main()
