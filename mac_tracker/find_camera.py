"""
Tries camera indices 0-4 one at a time, showing a preview window labeled with
the index so you can identify which number is which camera (built-in vs the
new ELP module). For each one that opens, press any key to move to the next;
press 'q' to stop early once you've found the one you're after.
"""
import cv2

def main():
    for index in range(5):
        cap = cv2.VideoCapture(index)
        if not cap.isOpened():
            print(f"Index {index}: not available")
            cap.release()
            continue

        ret, frame = cap.read()
        if not ret:
            print(f"Index {index}: opened but couldn't read a frame")
            cap.release()
            continue

        print(f"Index {index}: showing preview - press any key for next, 'q' to stop")
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            cv2.putText(frame, f"Camera index {index} - any key = next, q = stop",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.imshow("Find Camera", frame)
            key = cv2.waitKey(1) & 0xFF
            if key != 255:  # any key pressed
                if key == ord('q'):
                    cap.release()
                    cv2.destroyAllWindows()
                    return
                break

        cap.release()

    cv2.destroyAllWindows()
    print("Done checking indices 0-4.")

if __name__ == "__main__":
    main()
