from machine import Pin, PWM # PWM is used to control the servos (not python but micropython)
import sys # sys is used to read from standard input (stdin) for receiving commands from the host computer
import time # used for the gentle startup ramp below
# the host computer sends commands to the Pico over USB, which are read from stdin in this script

# Adjust these once servos are wired
PAN_PIN = 13 #gp13 4 above
TILT_PIN = 14 #gp14 2nd above

led = Pin("LED", Pin.OUT)  # Onboard LED - on a Pico W this is wired through the
                           # wireless chip, not GPIO25 like a plain Pico, so it
                           # must be addressed by name ("LED") not pin number.

pan_servo = PWM(Pin(PAN_PIN)) # Initialize the pan servo
tilt_servo = PWM(Pin(TILT_PIN)) # Initialize the tilt servo
pan_servo.freq(50) # Set the frequency of the PWM signal to 50Hz for the pan servo
tilt_servo.freq(50) # Set the frequency of the PWM signal to 50Hz for the tilt servo
# we chose 50Hz because it's a common frequency for hobby servos, which typically expect a pulse every 20ms (1/50Hz = 20ms).

# SG90 pulse range: ~0.5ms (0°) to ~2.5ms (180°) at 50Hz (20ms period)
MIN_DUTY = 1638   # ~0.5ms
MAX_DUTY = 8192   # ~2.5ms

def set_angle(servo, angle): # Set the angle of the servo (0-180 degrees)
    angle = max(0, min(180, angle))
    duty = int(MIN_DUTY + (MAX_DUTY - MIN_DUTY) * (angle / 180))
    servo.duty_u16(duty)

def ramp_to_angle(servo, target_angle, steps=25, step_delay_ms=25):
    # Eases into position gradually instead of snapping there instantly - this
    # is what runs at startup so power-on doesn't cause a sudden hard jump.
    # We don't know the servo's actual physical position at boot (no feedback
    # sensor), so we ramp up from a safe low duty rather than assume anything.
    target_angle = max(0, min(180, target_angle))
    target_duty = int(MIN_DUTY + (MAX_DUTY - MIN_DUTY) * (target_angle / 180))
    start_duty = MIN_DUTY
    for i in range(steps + 1):
        duty = int(start_duty + (target_duty - start_duty) * i / steps)
        servo.duty_u16(duty)
        time.sleep_ms(step_delay_ms)

def parse_command(line):
    # Expected format: "PAN:90,TILT:45" for normal angle commands (0-180, uses
    # MIN_DUTY/MAX_DUTY above), or "RAWPAN:3000" / "RAWTILT:5000" for direct
    # duty_u16 calibration commands (0-65535, bypasses the angle math entirely) -
    # used by calibrate_range.py to find the real safe pulse-width range.
    try:
        pan_angle = None
        tilt_angle = None
        raw_pan = None
        raw_tilt = None
        for part in line.strip().split(','):
            key, value = part.split(':')
            if key == 'PAN':
                pan_angle = int(value)
            elif key == 'TILT':
                tilt_angle = int(value)
            elif key == 'RAWPAN':
                raw_pan = int(value)
            elif key == 'RAWTILT':
                raw_tilt = int(value)
        return pan_angle, tilt_angle, raw_pan, raw_tilt
    except Exception:
        return None, None, None, None

def main():
    # IMPORTANT - power order matters: this only runs once, the moment the
    # Pico itself boots (USB plugged in, or reset). If the TalentCell
    # (servo power) is OFF at that moment, this ramp executes with no power
    # reaching the servo, so nothing physically moves - the servo just sits
    # wherever it happened to be. Then later, whenever the TalentCell is
    # switched on, the servo suddenly gets power and slams straight to
    # whatever duty is already sitting on the signal line, with no ramp,
    # because the ramp already ran earlier while unpowered and did nothing.
    # That's what was causing the power-on shoot-up/buzz.
    #
    # For this ramp to actually smooth anything out physically, the
    # TalentCell must already be ON *before* the Pico boots/resets:
    #   1. TalentCell ON first
    #   2. THEN plug in / reset the Pico
    # That way this code runs while the servo is actually powered.

    # Blink 3 times as a visible "this is the current firmware" marker -
    # confirms this exact code is what's running, no serial/REPL needed.
    for _ in range(3):
        led.on()
        time.sleep_ms(150)
        led.off()
        time.sleep_ms(150)

    ramp_to_angle(pan_servo, 90, steps=40, step_delay_ms=25)
    ramp_to_angle(tilt_servo, 90, steps=40, step_delay_ms=25)

    while True:
        line = sys.stdin.readline()
        if not line:
            continue
        pan_angle, tilt_angle, raw_pan, raw_tilt = parse_command(line)
        if pan_angle is not None:
            set_angle(pan_servo, pan_angle)
        if tilt_angle is not None:
            set_angle(tilt_servo, tilt_angle)
        if raw_pan is not None:
            pan_servo.duty_u16(max(0, min(65535, raw_pan)))
        if raw_tilt is not None:
            tilt_servo.duty_u16(max(0, min(65535, raw_tilt)))

if __name__ == "__main__":
    main()
