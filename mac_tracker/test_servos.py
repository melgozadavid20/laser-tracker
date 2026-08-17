"""
Quick standalone servo test - bypasses the vision pipeline entirely.
Sweeps pan, then tilt, so you can watch each servo in isolation and
confirm the hardware/wiring is good before trusting the full tracker.
"""
import time
from pico_serial import connect, send_angles

PICO_PORT = "/dev/tty.usbmodem14201"

ser = connect(PICO_PORT)
print(f"Connected to {PICO_PORT}")

# The Pico's firmware ramps to center itself at boot now (as long as the
# TalentCell was powered on BEFORE the Pico booted/reset - see
# pico_firmware/main.py). By the time this script connects, it should
# already be sitting at center, so we just confirm/hold it here.
print("Confirming center...")
send_angles(ser, 90, 90)
time.sleep(1)

print("Sweeping PAN (tilt held at 90)...")
for angle in [60, 90, 120, 90]:
    print(f"  PAN -> {angle}")
    send_angles(ser, angle, 90)
    time.sleep(1)

print("Sweeping TILT (pan held at 90)...")
for angle in [60, 90, 120, 90]:
    print(f"  TILT -> {angle}")
    send_angles(ser, 90, angle)
    time.sleep(1)

print("Done.")
ser.close()
