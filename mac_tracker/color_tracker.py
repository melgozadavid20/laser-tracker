# color_tracker.py
# Pipeline:
# 1. Open webcam
# 2. Capture frames
# 3. Convert frames to HSV colorspace
# 4. Create a mask for the target color (red in this case)
# 5. Find contours in the mask
# 6. Identify the largest contour and calculate its center
# 7. Calculate the offset of the center from the frame's center
import cv2 # cv2 is the OpenCV library for computer vision tasks
import numpy as np # great for numerical operations, especially with arrays

# HSV range for a red object (red wraps around 0/180 in HSV, so two ranges)
# Hue (actual color): 0-179
# Saturation (color intensity): 0-255
# Value (brightness): 0-255
LOWER_RED_1 = np.array([0, 120, 70]) # [0-10 = red-orange, 120-255 = excludes pale colors, 70-255 = excludes dark colors]
UPPER_RED_1 = np.array([10, 255, 255])
LOWER_RED_2 = np.array([170, 120, 70]) # [170-180 = red-magenta, 120-255 = excludes pale colors, 70-255 = excludes dark colors]
UPPER_RED_2 = np.array([180, 255, 255]) 
# Note: 120-255 and 70-255 to ensure we capture the bright red colors and exclude dark or pale colors

def main():
    cap = cv2.VideoCapture(1) # turn on the webcam (device index 1, change if necessary)
    if not cap.isOpened(): # check if the webcam is opened successfully
        print("Error: Could not open webcam.")
        return # exit the function if the webcam cannot be opened

    while True:
        ret, frame = cap.read() # grab a frame from the webcam; ret is a boolean indicating success, frame is the captured image
        if not ret:
            continue # skip this iteration if the frame was not captured successfully
        # 

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV) # converts BGR colorspace to HSV colorspace for easier color detection
        mask1 = cv2.inRange(hsv, LOWER_RED_1, UPPER_RED_1) # create a binary mask where red pixels are white (255) and others are black (0)
        mask2 = cv2.inRange(hsv, LOWER_RED_2, UPPER_RED_2) # create a second binary mask for the second red range
        mask = mask1 | mask2 # combine the two masks to capture all red pixels in the frame

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE) # find contours in the binary mask;
        # contours is a list of all detected contours, and _ is a placeholder for the hierarchy (not used here)
        #cv2.findContours(image, mode, method) -> contours, hierarchy
        #RETR_EXTERNAL: retrieves only the extreme outer contours
        #Chose this mode simply because we are only interested in the largest red object, not any nested contours
        #Nested contours is more relevant for complex shapes or when you want to detect holes inside objects, which we don't need here
        #CHAIN_APPROX_SIMPLE: compresses horizontal, vertical, and diagonal segments and leaves only their end points
        #Chose this method to save memory and processing time, as we don't need all the points of the contour, just the shape

        if contours: # if any contours are found
            largest = max(contours, key=cv2.contourArea) 
            if cv2.contourArea(largest) > 500:  # ignore tiny noise
                x, y, w, h = cv2.boundingRect(largest) # get the bounding rectangle of the largest contour
                cx, cy = x + w // 2, y + h // 2 
                

                frame_h, frame_w = frame.shape[:2] # frame.shape returns (height, width, channels); we only need height and width
                # here we used :2 to slice the first two elements of the shape tuple, which are height and width, ignoring the channels
                offset_x = cx - frame_w // 2 # calculate the horizontal offset of the detected object from the center of the frame
                offset_y = cy - frame_h // 2 # calculate the vertical offset of the detected object from the center of the frame

                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2) # draw a green rectangle around the detected object;
                # cv2.rectangle(image, pt1, pt2, color, thickness) -> (0, 255, 0) is green in BGR format, and thickness=2 pixels
                cv2.circle(frame, (cx, cy), 5, (255, 0, 0), -1) # draw a blue circle at the center of the detected object; 
                # cv2.circle(image, center, radius, color, thickness) -> (255, 0, 0) is blue in BGR format, and thickness=-1 
                # -1 fills the circle
                print(f"Target offset -> x: {offset_x}, y: {offset_y}") # print the offset values to the console for debugging 
                # and tracking purposes

        cv2.imshow("Color Tracker", frame) # display the frame with the detected object highlighted in a window titled "Color Tracker"
        if cv2.waitKey(1) & 0xFF == ord('q'): # wait for the 'q' key to be pressed; if pressed, exit the loop and close the program
            break

    cap.release() # release the webcam resource to free it up for other applications
    cv2.destroyAllWindows() # close all OpenCV windows to clean up the GUI and free resources

if __name__ == "__main__":
    main()