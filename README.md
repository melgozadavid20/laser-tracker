# Laser Tracker

Real-time hand tracking driving a pan-tilt laser. A host application detects a
hand in the webcam feed, converts its position into pan/tilt angles, and streams
servo commands to a Raspberry Pi Pico WH over serial — a closed loop from camera
frame to physical actuator.

## Demo

https://github.com/user-attachments/assets/f11a5104-fb74-4ec2-b0a1-c348f6b1e666

## Architecture

The system is split across two machines: perception runs on the host, actuator
control runs on the microcontroller.

**`mac_tracker/`** — Python, MediaPipe, OpenCV, NumPy. Detects hand landmarks in
each frame, maps normalized image coordinates to target pan/tilt angles, and
sends them over serial. Includes calibration tooling to align the camera frame
with servo travel, and an on-screen state overlay reporting tracking status.

**`pico_firmware/`** — MicroPython on a Raspberry Pi Pico WH. Receives target
angles over serial, generates PWM for two SG90 servos on a pan-tilt bracket, and
drives the laser module.

## Hardware

| Component | Part |
|---|---|
| Microcontroller | Raspberry Pi Pico WH |
| Actuators | 2x SG90 micro servos, nylon pan-tilt bracket |
| Emitter | 650nm 5mW laser diode module |
| Camera | Host webcam |
