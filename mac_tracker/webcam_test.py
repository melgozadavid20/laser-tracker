# webcam_test.py
# Pipeline:
# 1. Open webcam
# 2. Capture frames
# 3. Display frames in a window 
import cv2  # cv2 is the OpenCV library for computer vision tasks
import time

def main():
    cap = cv2.VideoCapture(1)  # captures video from the webcam (device index 1, change if necessary)

    if not cap.isOpened():  # Check if the webcam is opened successfully
        print("Error: Could not open webcam.")
        return # exit the function if the webcam cannot be opened
    print("Webcam opened successfully. Press 'q' to quit.") # else, success message

    time.sleep(1)  # let the camera warm up before grabbing frames

    fail_count = 0 # Initialize a counter for failed frame captures
    while True:
        ret, frame = cap.read() # grabs a frame from the webcam; ret is a boolean indicating success, frame is the captured image
        if not ret:  # Check if the frame was captured successfully
            fail_count += 1
            if fail_count > 30:  # bail only after repeated failures
                print("Error: Could not read frame after multiple retries.")
                break # exit the loop if too many failures occur
            time.sleep(0.1) # wait a bit before retrying to avoid false positives
            continue # continue to the next iteration of the loop to try capturing again
        fail_count = 0 # reinitialize the fail count on successful capture

        cv2.imshow('Webcam Test', frame)  # Display the captured frame in a window

        if cv2.waitKey(1) & 0xFF == ord('q'):  # Wait for 'q' key to exit
            break # exit the loop if 'q' is pressed

    cap.release()  # Release the webcam
    cv2.destroyAllWindows()  # Close all OpenCV windows

if __name__ == "__main__":
    main()  # Call the main function to run the webcam test