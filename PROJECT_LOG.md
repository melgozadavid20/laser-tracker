# Laser Tracker — Session Log

## 2026-08-17 — Camera moved onto the bracket; closed-loop pursuit tracking

**Big picture change:** the webcam used to sit stationary (on the MacBook)
while the pan/tilt bracket + laser moved independently, tracked via a
calibrated open-loop mapping (`GAIN_X`/`GAIN_Y` + a measured "aim center").
That mapping broke any time the camera or bracket got bumped, and required
re-calibrating from scratch. Fixed by physically mounting a small USB camera
(ELP super-mini 720p module) directly on the bracket next to the laser, so
camera and laser now move together and always point the same direction.
Tracking logic changed to match: `tracker_main.py` now does closed-loop
**pursuit** — each frame it nudges pan/tilt a small capped step to keep the
hand at a target frame position, instead of computing an absolute angle from
a calibrated mapping. Frame-center (adjusted by a small fixed aim-offset,
see below) represents wherever the laser currently points, by construction.

### Hardware bring-up (SG90s, Pico, TalentCell) — the bulk of the debugging
- Diagnosed a recurring "servo shoots up and buzzes the instant TalentCell
  powers on" issue over many sessions. Root causes, in order found:
  1. Stopping the Python script didn't stop the Pico's PWM output — it holds
     the last command indefinitely. Fixed with a `try/finally` in
     `tracker_main.py` that always sends a recenter command on exit.
  2. The firmware's startup ramp only runs once, at Pico boot — not every
     time servo power (TalentCell) is toggled. Since Pico logic power (USB)
     and servo power (TalentCell) are separate, by the time TalentCell
     powers on, the Pico's usually already finished ramping to a stale
     value and just snaps to it with no ramp. **Fix: power order matters —
     TalentCell must be ON *before* the Pico boots/resets**, so the ramp
     actually executes while the servo has power. This is now the standard
     startup routine for every test.
  3. Commanding tilt to 90° ("center") was itself intermittently too far —
     matches earlier findings that tilt reached ~3/4 of its travel at
     "90", not centered. This got resolved by the camera-on-bracket
     redesign (pursuit doesn't depend on 90 being a meaningful aim point
     anymore) rather than by finding a "real" safe duty range.
  4. Also fixed: Pico W's onboard LED isn't on GPIO25 like a plain Pico
     (wired through the CYW43 wireless chip instead) — must use
     `Pin("LED", Pin.OUT)`, not `Pin(25, ...)`. Used as a 3-blink boot
     marker to confirm new firmware actually uploaded before trusting any
     other test result.
  5. Physical causes also found and fixed along the way: a zip-tied wire
     snagging the tilt joint, and the SG90 horn slipping off its shaft
     under vibration (re-seated + can add thread-locker if it recurs).
- New bracket (SG90s) swapped in later in the session; behaves well with
  the same TalentCell-then-Pico startup routine.
- **`pico_firmware/main.py`**: ramps both servos to 90° at boot (only
  meaningful if TalentCell was already on — see above). Backup of this
  exact "production" version saved as
  `pico_firmware/main_with_startup_ramp.py` in case a debug/no-auto-move
  variant is needed again for isolated hardware testing.

### New camera + pursuit tracking
- **`mac_tracker/tracker_main.py`**: removed the old open-loop
  `GAIN_X`/`GAIN_Y`/`PAN_AIM_CENTER`/`TILT_AIM_CENTER` calibration and all
  laser-color detection (`find_laser_dot`, HSV thresholds) — no longer
  needed since the laser doesn't need to be visually found anymore. Added:
  - `CAMERA_INDEX` — the new bracket-mounted camera's device index (found
    via `find_camera.py`).
  - `PURSUIT_GAIN_X`/`PURSUIT_GAIN_Y`/`PURSUIT_MAX_STEP` — incremental,
    capped per-frame nudging toward keeping the hand centered.
  - `AIM_OFFSET_X`/`AIM_OFFSET_Y` (pixels) — compensates for the laser not
    being exactly coincident with the camera lens (parallax, like a scope
    mounted above a barrel). Pursuit targets this offset frame position
    instead of true center. Measured via `calibrate_trim.py`.
    Current values: `AIM_OFFSET_X = 350`, `AIM_OFFSET_Y = -105`.
  - `INVERT_PAN`/`INVERT_TILT` may need re-checking any time the camera's
    physical mounting changes, since the servo-to-frame-motion relationship
    depends on it.
- **New file: `mac_tracker/find_camera.py`** — cycles camera indices 0-4
  with a labeled preview so you can identify which index is which camera.
- **New file: `mac_tracker/calibrate_trim.py`** — runs the real pursuit
  loop live while you jog the aim-offset target with arrow keys/WASD until
  the physical laser lands on your hand. (An earlier version tried adding a
  correction *after* pursuit computed its target — that failed, since
  pursuit's whole job is re-centering the hand and just cancelled the
  correction back out. Moving the *target* instead of the *output* is what
  made it stable.)
- **New file: `mac_tracker/laser_hsv_probe.py`** — click-to-sample HSV
  values from a live (freezable) camera feed. Built while still trying to
  tune laser-color detection, before switching to the camera-on-bracket
  approach made that unnecessary. Kept in case laser-color detection is
  ever revisited.
- **Now-legacy/unused files** (kept for reference, not part of the current
  pipeline): `calibrate_gain.py` and `laser_detect_test.py` — built for the
  old open-loop, stationary-camera architecture. `calibrate_gain.py`'s
  CENTER-point-first approach was a precursor to `calibrate_trim.py`.

### Other additions this session
- **`mac_tracker/test_range.py`**, **`calibrate_range.py`**,
  **`calibrate_step.py`**, **`manual_control.py`** — various hardware
  diagnostic/calibration tools built while chasing the servo-buzzing issue.
  `manual_control.py` (arrow-key/WASD manual nudging with a live pan/tilt
  readout) is the most broadly reusable one if hardware behaves oddly again.
- **`mac_tracker/tracker_main.py`** also gained an init sequence: shows
  "Initializing - centering mount..." then a brief "CENTERED - ready!" flash
  before tracking starts, so you're never guessing whether it's safe to
  move your hand yet.
- Current tuning: `SMOOTHING = 0.4`, `PURSUIT_GAIN_X = PURSUIT_GAIN_Y =
  0.045`, `PURSUIT_MAX_STEP = 4` — tuned snappier after the co-located
  camera made the old, more conservative values feel sluggish.
- `PICO_PORT` drifts (e.g. between `.../usbmodem14101` and `.../14201`)
  any time the Pico is unplugged/replugged — check with `ls /dev/tty.*` if
  a script reports it can't connect.

### Standard routine going forward
1. TalentCell OFF, Pico unplugged.
2. TalentCell ON first.
3. Then plug in / reset the Pico — watch for 3 LED blinks, then the ramp to
   center.
4. Run whichever script (`tracker_main.py` for the real thing,
   `test_servos.py`/`manual_control.py` for hardware checks).
5. Reset the Pico fresh before each new test session rather than just
   cycling TalentCell — avoids stale latched commands.

### Verified
- Pursuit tracking runs live, laser lands accurately on hand after
  `calibrate_trim.py` calibration, feels responsive at the current gain
  settings. Demo recorded successfully.
- All of this session's changes committed and pushed to
  `github.com/melgozadavid20/laser-tracker`.

---

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
