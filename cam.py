import cv2
import pytesseract
from pytesseract import Output
import time
from time import sleep
#import RTk.GPIO as GPIO

cap = cv2.VideoCapture(0) # If camera is not working try switching to 1 instead of 0
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
cap.set(cv2.CAP_PROP_FPS, 60)
width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
print('Width and Height of frame: [' + str(width) + ":" + str(height) + ']')
#c
current_dimensions = [300,400,200,400] # Portion of frame to scan (y1,y2,x1,x2)
color_thresh = 150 # BW color threshhold

while True:
    
    ret, frame = cap.read() # Capture frame-by-frame

    cropFrame = frame[current_dimensions[0]:current_dimensions[1],current_dimensions[2]:current_dimensions[3]]

    gray = cv2.cvtColor(cropFrame, cv2.COLOR_BGR2GRAY) # Converts to grayscale
    #cv2.imshow('gray', gray)
    ret, bw = cv2.threshold(gray,150,255, cv2.THRESH_BINARY)
    cv2.startWindowThread()
    cv2.namedWindow("BW portion of frame being scanned")
    cv2.moveWindow("BW portion of frame being scanned", 700, 50)
    cv2.imshow("BW portion of frame being scanned", bw)

    data = pytesseract.image_to_data(bw, lang = 'eng', output_type=Output.DICT) # Actual OCR command
    reading = ''

    # Drawing grid lines and markers
    for y in range(0,480,50):
        frame = cv2.line(frame, (0,y), (640,y), (0,0,255), 1)
        frame = cv2.putText(frame, str(y), (0,y), cv2.FONT_HERSHEY_PLAIN, 1, (0, 255,100), 1)
    for x in range(0,640,50):
        frame = cv2.line(frame, (x,0), (x,480), (0,0,255), 1) 
        frame = cv2.putText(frame, str(x), (x,10), cv2.FONT_HERSHEY_PLAIN, 1, (0, 255,100), 1)

    n_boxes = len(data['text'])
    # Draw portion of frame being scanned
    frame = cv2.rectangle(frame, (current_dimensions[2], current_dimensions[0]), (current_dimensions[3], current_dimensions[1]), (255, 255, 255), 2)
    for i in range(n_boxes):
        if int(float(data['conf'][i])) > 50: # Integer is confidence level of word being read 
            (text, x, y, w, h) = (data['text'][i], data['left'][i], data['top'][i], data['width'][i], data['height'][i])
            if text and text.strip() != "":
                reading += (text)
                frame = cv2.rectangle(frame, (x + current_dimensions[2], y + current_dimensions[0]), (x + w + current_dimensions[2], y + h + current_dimensions[0]), (0, 255, 0), 2)
                frame = cv2.putText(frame, text, (x + current_dimensions[2], y - 10 + current_dimensions[0]), cv2.FONT_HERSHEY_PLAIN, 1, (0, 0, 255), 2)
    
    # Display the resulting frame
    cv2.startWindowThread()
    cv2.namedWindow("Camera Feed")
    cv2.moveWindow("Camera Feed", 10,50)
    cv2.imshow("Camera Feed", frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# When everything done, release the capture
cap.release()
cv2.destroyAllWindows()
 