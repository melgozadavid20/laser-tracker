# pico_serial.py
# Pipeline:
# 1. Connect to the Pico over USB
# 2. Send pan and tilt angles to the Pico over serial
# 3. Pico receives the angles and moves the servos accordingly
import serial # Serial library for communication with the Pico over USB
import time

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


def ease_to_angles(ser, start_pan, start_tilt, target_pan, target_tilt, steps=20, step_delay=0.03):
    """Gradually walks from a starting angle to a target angle instead of
    jumping straight there in one command. The Pico now idles at a safe LOW
    duty at boot rather than assuming center is safe, so it's on the HOST
    side (here) to ease up to center itself once a script connects and a
    human is present/watching - rather than relying on the Pico to do it
    unattended at boot, which is what caused the power-on snap before."""
    for i in range(steps + 1):
        pan = start_pan + (target_pan - start_pan) * i / steps
        tilt = start_tilt + (target_tilt - start_tilt) * i / steps
        send_angles(ser, round(pan), round(tilt))
        time.sleep(step_delay)