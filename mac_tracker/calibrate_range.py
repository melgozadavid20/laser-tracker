"""
Finds the REAL safe pulse-width range for the tilt (and pan) servo, instead of
trusting the generic 0.5ms-2.5ms textbook range currently coded into
pico_firmware/main.py's MIN_DUTY/MAX_DUTY.

This sends raw duty_u16 values directly (bypassing the 0-180 angle math), and
steps from a low value up to a high one in small increments across the whole
plausible range. No assumption is made about where "center" should be - we're
mapping it fresh.

REQUIRES pico_firmware/main.py to have the RAWPAN/RAWTILT command support.
Make sure that updated firmware is actually saved onto the Pico as main.py
before running this (same way you'd upload any other firmware change).

Watch and listen closely at every step. You're looking for:
  - Where it STARTS moving smoothly (the real low end of usable range)
  - Where it STOPS being able to keep up / starts straining or grinding
    (the real high end)
The moment you hear sustained straining (not just brief motion whine), note
the duty value just printed and press Ctrl-C.
"""
import time
from pico_serial import connect

PICO_PORT = "/dev/tty.usbmodem14201"

START_DUTY = 1000   # ~0.3ms - below any realistic servo range, safe starting point
END_DUTY = 8500      # ~2.6ms - just past the old assumed max
STEP = 200            # ~0.06ms per step
PAUSE = 0.6           # seconds to settle + listen at each step

def duty_to_ms(duty):
    return duty / 65535 * 20.0  # 20ms period at 50Hz

def send_raw(ser, key, duty):
    ser.write(f"{key}:{int(duty)}\n".encode())

def sweep(ser, key):
    duty = START_DUTY
    while duty <= END_DUTY:
        send_raw(ser, key, duty)
        print(f"  {key} duty={int(duty)} (~{duty_to_ms(duty):.2f}ms)")
        time.sleep(PAUSE)
        duty += STEP

def main():
    ser = connect(PICO_PORT)
    print(f"Connected to {PICO_PORT}")

    # Park pan at a safe assumed-center while we test tilt in isolation.
    send_raw(ser, "RAWPAN", 4915)

    print(f"\nTILT sweep from {START_DUTY} to {END_DUTY} - listen closely:")
    sweep(ser, "RAWTILT")

    print("\nDone with tilt sweep. Returning tilt to a safe low value.")
    send_raw(ser, "RAWTILT", START_DUTY)

    input("\nPress Enter to also sweep PAN the same way (or Ctrl-C to stop here)...")
    print(f"\nPAN sweep from {START_DUTY} to {END_DUTY} - listen closely:")
    sweep(ser, "RAWPAN")

    print("\nDone. Both servos left at their last commanded position.")
    ser.close()

if __name__ == "__main__":
    main()
