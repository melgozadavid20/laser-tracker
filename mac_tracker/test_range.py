"""
Finds the real safe mechanical range of the pan/tilt SG90s, rather than assuming
the generic 0-180 range is safe. Steps each servo outward from center in small
increments, pausing at each step so you can listen/watch for straining or
grinding BEFORE it gets bad - unlike test_servos.py, which jumps straight to
60/90/120 and could already be past a real limit.

Watch and listen closely. The moment you hear/see straining (not just normal
servo whine while moving, but a sustained grind/hum once it should have
stopped), note the angle printed and stop the script (Ctrl-C - it will still
recenter on exit). That angle is the real edge of safe travel for that servo,
not 0 or 180.
"""
import time
from pico_serial import connect, send_angles

PICO_PORT = "/dev/tty.usbmodem14201"
STEP = 10          # degrees per step
PAUSE = 0.6        # seconds to settle + listen at each step

def sweep(ser, axis, other_axis_angle, direction):
    """axis: 'PAN' or 'TILT'. direction: +1 or -1 from center."""
    angle = 90
    while 0 <= angle <= 180:
        pan = angle if axis == "PAN" else other_axis_angle
        tilt = angle if axis == "TILT" else other_axis_angle
        send_angles(ser, pan, tilt)
        print(f"  {axis} -> {angle}")
        time.sleep(PAUSE)
        angle += STEP * direction

def main():
    ser = connect(PICO_PORT)
    print(f"Connected to {PICO_PORT}")

    print("Centering...")
    send_angles(ser, 90, 90)
    time.sleep(1)

    print("\nPAN outward toward 180 (tilt held at 90) - listen for straining:")
    sweep(ser, "PAN", 90, +1)
    print("Back to center...")
    send_angles(ser, 90, 90)
    time.sleep(1)

    print("\nPAN outward toward 0 (tilt held at 90) - listen for straining:")
    sweep(ser, "PAN", 90, -1)
    send_angles(ser, 90, 90)
    time.sleep(1)

    print("\nTILT outward toward 180 (pan held at 90) - listen for straining:")
    sweep(ser, "TILT", 90, +1)
    send_angles(ser, 90, 90)
    time.sleep(1)

    print("\nTILT outward toward 0 (pan held at 90) - listen for straining:")
    sweep(ser, "TILT", 90, -1)
    send_angles(ser, 90, 90)

    print("\nDone - fully centered.")
    ser.close()

if __name__ == "__main__":
    main()
