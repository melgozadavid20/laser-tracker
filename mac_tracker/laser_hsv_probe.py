"""
Diagnostic tool: click anywhere on the live camera feed to print that pixel's
actual HSV values to the terminal. Read-only, no Pico connection at all.

Use this to find out what the REAL laser dot looks like to this camera,
instead of guessing HSV ranges. Point the laser at a plain, dim/dark surface
(not your monitor or anything else bright), let the dot show up clearly in
the window, then click directly on the brightest/reddest part of it. Do this
a few times (dot center, and maybe a slightly dimmer edge pixel) to see the
real range, since laser dots often bloom out to white/pink at the very
center with a more saturated red ring around it.

Also click on a few things that were falsely triggering detection before
(like your monitor) so we can see what's confusing it - the goal is to find
HSV ranges that catch the real dot but exclude those.

The live feed updates too fast to click a small moving dot precisely, so:
  SPACE  - freeze/unfreeze the current frame
  q      - quit
Freeze it once the laser dot is clearly visible, then click carefully.
"""
import cv2

def on_mouse(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        frame = param["frame"]
        if frame is None:
            return
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        h, s, v = hsv[y, x]
        b, g, r = frame[y, x]
        print(f"Clicked ({x},{y})  ->  HSV=({h},{s},{v})   BGR=({b},{g},{r})")

def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: could not open webcam.")
        return

    window = "HSV Probe - SPACE to freeze, click to sample, q to quit"
    cv2.namedWindow(window)
    param = {"frame": None}
    cv2.setMouseCallback(window, on_mouse, param)

    print("Move the laser into position, press SPACE to freeze the frame, then click")
    print("carefully on the dot. Press SPACE again to unfreeze. Press 'q' to quit.\n")

    frozen = False
    current_frame = None

    while True:
        if not frozen:
            ret, frame = cap.read()
            if not ret:
                continue
            current_frame = frame
            param["frame"] = frame

        display = current_frame.copy()
        if frozen:
            cv2.putText(display, "FROZEN - click to sample, SPACE to unfreeze",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
        cv2.imshow(window, display)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord(' '):
            frozen = not frozen

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
