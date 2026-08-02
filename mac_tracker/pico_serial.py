# pico_serial.py
# Pipeline:
# 1. Connect to the Pico over USB
# 2. Send pan and tilt angles to the Pico over serial
# 3. Pico receives the angles and moves the servos accordingly
import serial # Serial library for communication with the Pico over USB

BAUD_RATE = 115200 # Baud rate for the serial connection

def connect(port): # Connect to the Pico over USB
    """port example on macOS: '/dev/tty.usbmodem14201' (find via `ls /dev/tty.*` with Pico plugged in)"""
    return serial.Serial(port, BAUD_RATE, timeout=1) # Return the serial connection
# port is used for specifying the serial port to which the Pico is connected. 
# The baud rate is set to 115200, which is a common speed for serial communication. 
# The timeout parameter ensures that the read operations do not block indefinitely.


def send_angles(ser, pan_angle, tilt_angle): # Send pan and tilt angles to the Pico over serial
    # ser is the serial connection object, pan_angle and tilt_angle are the angles to be sent to the Pico
    command = f"PAN:{pan_angle},TILT:{tilt_angle}\n" # output format: "PAN:90,TILT:45" (example)
    ser.write(command.encode()) # Encode the command string to bytes and send it over the serial connection to the Pico