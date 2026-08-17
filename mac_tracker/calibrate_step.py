"""
Manual, step-at-a-time version of the tilt calibration - no automatic timing,
no rushing. You control the pace entirely: press Enter to send the next duty
value, listen/watch, and only press Enter again when you're ready. Type 'q'
and Enter at any point to stop where you are.

Start with the TalentCell OFF. Run this script, and when it prints the first
duty value and waits, THEN power on the TalentCell - that first value (1000,
a low/gentle pulse) is what it'll be holding the moment power arrives.
"""
from pico_serial import connect

PICO_PORT = "/dev/tty.usbmodem14201"
START_DUTY = 1000
STEP = 150

def duty_to_ms(duty):
    return duty / 65535 * 20.0

def main():
    ser = connect(PICO_PORT)
    print(f"Connected to {PICO_PORT}\n")

    duty = START_DUTY
    print(f"About to send TILT duty={duty} (~{duty_to_ms(duty):.2f}ms).")
    print("Power on the TalentCell now if you haven't already, then:")

    while True:
        cmd = input(f"Press Enter to send TILT duty={duty} (~{duty_to_ms(duty):.2f}ms), or 'q' to stop: ")
        if cmd.strip().lower() == 'q':
            break
        ser.write(f"RAWTILT:{duty}\n".encode())
        print(f"  -> sent duty={duty} (~{duty_to_ms(duty):.2f}ms)")
        duty += STEP

    print(f"\nStopped at duty={duty - STEP} (~{duty_to_ms(duty - STEP):.2f}ms).")
    print("That's the last value it should have looked/sounded OK at.")
    ser.close()

if __name__ == "__main__":
    main()
