"""
Interactive manual control - move the pan/tilt mount yourself with the
keyboard, one small step at a time. This tests the servos through their
NORMAL angle-based range (same path tracker_main.py and test_servos.py use),
centered around 90/90 - which is the actual value that's been causing
buzzing, and which the raw duty_u16 sweeps (calibrate_step.py /
calibrate_range.py, starting at duty=1000) never actually reached.

Use this to answer: is 90 itself already too far for tilt? Can you nudge a
few degrees off center safely? Where exactly does it start to strain?

IMPORTANT: the moment this script connects, it immediately sends (90, 90) -
that's the known problem value. Start with the TalentCell OFF, run the
script, THEN power on the TalentCell once it's ready and watch/listen
closely for that very first transition.

Controls (click into the small window first so it has keyboard focus):
  Arrow keys or W/A/S/D  - nudge tilt up/down, pan left/right by 5 degrees
  C                      - jump back to center (90, 90)
  Q or Esc               - quit (recenters and disconnects safely)
"""
import cv2
import numpy as np
from pico_serial import connect, send_angles

PICO_PORT = "/dev/tty.usbmodem14201"
STEP = 5
CENTER_ANGLE = 90

def main():
    ser = connect(PICO_PORT)
    print(f"Connected to {PICO_PORT}")

    pan = CENTER_ANGLE
    tilt = CENTER_ANGLE

    print("\nAbout to send initial center (90, 90).")
    print("Power on the TalentCell now if you haven't already, then watch closely.\n")
    input("Press Enter when ready to send it: ")
    send_angles(ser, pan, tilt)
    print(f"  PAN={pan}  TILT={tilt}")

    window = "Manual Servo Control - click here, use arrows/WASD"
    cv2.namedWindow(window)

    print("\nControls: arrows or WASD to nudge 5 degrees, C to recenter, Q/Esc to quit.")
    print("Watch/listen closely after every single press.\n")

    try:
        while True:
            canvas = np.zeros((220, 560, 3), dtype=np.uint8)
            cv2.putText(canvas, f"PAN: {pan}", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            cv2.putText(canvas, f"TILT: {tilt}", (20, 110), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            cv2.putText(canvas, "Arrows/WASD = nudge 5deg, C = center, Q = quit",
                        (20, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
            cv2.putText(canvas, "Watch/listen after every press", (20, 190),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (150, 150, 150), 1)
            cv2.imshow(window, canvas)

            key = cv2.waitKeyEx(50)
            if key == -1:
                continue

            moved = False
            if key in (81, 2424832, 63234, ord('a'), ord('A')):       # left
                pan = max(0, pan - STEP); moved = True
            elif key in (83, 2555904, 63235, ord('d'), ord('D')):     # right
                pan = min(180, pan + STEP); moved = True
            elif key in (82, 2490368, 63232, ord('w'), ord('W')):     # up
                tilt = max(0, tilt - STEP); moved = True
            elif key in (84, 2621440, 63233, ord('s'), ord('S')):     # down
                tilt = min(180, tilt + STEP); moved = True
            elif key in (ord('c'), ord('C')):
                pan, tilt = CENTER_ANGLE, CENTER_ANGLE; moved = True
            elif key in (ord('q'), ord('Q'), 27):
                break

            if moved:
                send_angles(ser, pan, tilt)
                print(f"  PAN={pan}  TILT={tilt}")
    finally:
        # NOT recentering to 90/90 here anymore - we now know 90 itself can
        # be an unsafe/straining position for tilt, so blindly "recentering"
        # on exit was actually leaving a bad value latched on the Pico,
        # which then caused the freak-out the next time TalentCell power was
        # applied (even before any new command was sent). Instead, just stop
        # sending anything and leave it at whatever the last confirmed-fine
        # position was.
        print(f"\nStopping here - last position sent was PAN={pan} TILT={tilt}.")
        print("Power off the TalentCell now before doing anything else.")
        cv2.destroyAllWindows()
        ser.close()

if __name__ == "__main__":
    main()
