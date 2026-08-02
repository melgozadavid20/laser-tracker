# Laser Tracker — Session Log

## 2026-08-02 — Switched hand detection from skin-color to MediaPipe

**Goal:** Replace the HSV skin-color masking in `mac_tracker/tracker_main.py`
with real hand tracking, since skin-color masking is unreliable (fires on
faces/arms/wood, breaks under different lighting or skin tones).

### What changed
- **`mac_tracker/tracker_main.py`** (~15–20 lines swapped, rest untouched):
  - Removed: `LOWER_SKIN`/`UPPER_SKIN` HSV constants, the
    `cv2.cvtColor` → `cv2.inRange` → `cv2.findContours` skin-mask pipeline.
  - Added: MediaPipe Hands (`mp.solutions.hands.Hands(...)`), which returns
    21 skeletal landmarks per detected hand. We use landmark 9
    (`MIDDLE_FINGER_MCP`, roughly the palm center) as the tracked point —
    steadier frame-to-frame than a fingertip or the wrist.
  - Unchanged: webcam capture loop, `offset_to_angles()` pan/tilt math,
    Pico serial connect/send logic.
- **New file: `mac_tracker/requirements.txt`** — lists `opencv-python`,
  `mediapipe`, `pyserial`. Notes that mediapipe only supports Python
  3.9–3.12 (not 3.13/3.14).
- **Not touched:** `color_tracker.py`, `webcam_test.py`, `pico_serial.py`,
  `pico_firmware/main.py`.

### Environment setup (this was most of the actual work)
- Original `venv/` was built on Python 3.14 — mediapipe doesn't support it.
- Installed Python 3.12 via Homebrew (`brew install python@3.12`); had to
  run `sudo xcodebuild -license accept` first since Xcode license wasn't
  accepted yet.
- Created a **separate venv**: `venv312/` (the old `venv/` on 3.14 is still
  there, just unused for this script now).
- `source venv312/bin/activate && pip install -r mac_tracker/requirements.txt`
  — installed cleanly.

### Verified
- Ran `python mac_tracker/tracker_main.py` inside `venv312` — webcam window
  opened, hand landmarks drew correctly, palm-center dot tracked the hand.
- Pico hardware wasn't connected during this test, so it ran in
  vision-only mode (prints `Pan: X, Tilt: Y` to the terminal instead of
  sending serial commands) — this is expected/handled gracefully by the
  existing `try/except` around `connect()`.

### Where things stand / possible next steps
- `PICO_PORT`, `CENTER_ANGLE`, `GAIN_X`, `GAIN_Y` in `tracker_main.py` are
  still placeholder values — need tuning once the Pico + pan/tilt hardware
  is actually mounted.
- Could swap the tracked landmark from palm-center (9) to a fingertip
  (e.g. index tip, landmark 8) if a more "pointing" feel is wanted instead
  of whole-hand centering.
- To run this again: **use `venv312`, not the old `venv/`** — that's the
  one with mediapipe installed for Python 3.12.
