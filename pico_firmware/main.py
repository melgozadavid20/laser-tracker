from machine import Pin, PWM # PWM is used to control the servos (not python but micropython)
import sys # sys is used to read from standard input (stdin) for receiving commands from the host computer
# the host computer sends commands to the Pico over USB, which are read from stdin in this script

# Adjust these once servos are wired
PAN_PIN = 13 #gp13 4 above
TILT_PIN = 14 #gp14 2nd above

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

def parse_command(line):
    # Expected format: "PAN:90,TILT:45"
    try:
        pan_angle = None
        tilt_angle = None
        for part in line.strip().split(','):
            key, value = part.split(':')
            if key == 'PAN':
                pan_angle = int(value)
            elif key == 'TILT':
                tilt_angle = int(value)
        return pan_angle, tilt_angle
    except Exception:
        return None, None

def main():
    set_angle(pan_servo, 90)   # center on startup
    set_angle(tilt_servo, 90)

    while True:
        line = sys.stdin.readline()
        if not line:
            continue
        pan_angle, tilt_angle = parse_command(line)
        if pan_angle is not None:
            set_angle(pan_servo, pan_angle)
        if tilt_angle is not None:
            set_angle(tilt_servo, tilt_angle)

if __name__ == "__main__":
    main()