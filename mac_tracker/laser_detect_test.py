"""
Read-only laser dot detection tester. Shows the webcam feed with a green ring
drawn wherever find_laser_dot() thinks the laser is - but never connects to the
Pico and never sends a single servo command. Completely safe to run while
pointing the laser around and checking whether detection tracks the real dot
or locks onto something else (skin, LEDs, reflections, etc).

Use this to tune LASER_HSV_RANGES / LASER_MIN_AREA / LASER_MAX_AREA in
tracker_main.py BEFORE ever setting ENABLE_LASER_TRACKING = True again.
"""
import cv2
from tracker_main import find_laser_dot

def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    print("Move the laser around and watch the green ring. Press 'q' to quit.")
    print("No servo commands are sent by this script - it's detection-only.")

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        laser_pos = find_laser_dot(frame)
        if laser_pos is not None:
            lx, ly = laser_pos
            cv2.circle(frame, (lx, ly), 12, (0, 255, 0), 2)
            cv2.putText(frame, f"laser: ({lx}, {ly})", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        else:
            cv2.putText(frame, "laser: not detected", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        cv2.imshow("Laser Detection Test (read-only)", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
