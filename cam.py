import cv2
import pytesseract
from pytesseract import Output
import time
from time import sleep
import RTk.GPIO as GPIO

#TAP = 4
#GPIO.setmode(GPIO.BCM)
#
#GPIO.setup(TAP, GPIO.OUT)
#GPIO.setup(6, GPIO.OUT)
#GPIO.setup(26, GPIO.OUT)
#
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
cap.set(cv2.CAP_PROP_FPS, 60)
width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
print(width, height)
start = time.time()
GPIO.setup(3, GPIO.OUT)
GPIO.setup(4, GPIO.OUT)
GPIO.setup(17, GPIO.OUT)
GPIO.setup(18, GPIO.OUT)
GPIO.output(3, GPIO.HIGH)
GPIO.output(4, GPIO.HIGH)
GPIO.output(17, GPIO.HIGH)
GPIO.output(18, GPIO.HIGH)

GPIO.output(17, GPIO.LOW)
GPIO.output(18, GPIO.HIGH)
sleep(5)
GPIO.output(17, GPIO.HIGH)
GPIO.output(18, GPIO.LOW)
sleep(5)
GPIO.output(17, GPIO.HIGH)
GPIO.output(18, GPIO.HIGH)
while True:

    if((time.time() - start) > 10000):
        cap.release()
        GPIO.output(3, GPIO.LOW)
        sleep(.2)
        GPIO.output(3, GPIO.HIGH)

#         GPIO.output(6, GPIO.HIGH)
#         GPIO.output(26, GPIO.LOW)
#         sleep(.2)
#         GPIO.output(6, GPIO.LOW)
#         GPIO.output(26, GPIO.LOW)
#         sleep(.2)
#        else:
#             GPIO.output(4, GPIO.LOW)
        start = time.time()
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_FPS, 60)
#         cv2.VideoCapture(0).release()
#         GPIO.output(4, GPIO.HIGH)
#         sleep(.2)
#         cap = cv2.VideoCapture(0)
        #GPIO.output(4, GPIO.LOW)

    current_dimensions = [250,300,200,350]
    reading = ''
    ret, frame = cap.read()# Capture frame-by-frame
    #print(ret)
    #frame = cv2.resize(frame, (350, 250), fx=0, fy=0, interpolation = cv2.INTER_AREA)
    cropFrame = frame[current_dimensions[0]:current_dimensions[1],current_dimensions[2]:current_dimensions[3]]

    gray = cv2.cvtColor(cropFrame, cv2.COLOR_BGR2GRAY)
    #cv2.imshow('gray', gray)
    ret, bw = cv2.threshold(gray, 140,255, cv2.THRESH_BINARY)
    cv2.startWindowThread()
    cv2.namedWindow("bw")
    cv2.moveWindow("bw", 100, 50)
    cv2.imshow("bw", bw)
    data = pytesseract.image_to_data(bw, lang = 'eng', output_type=Output.DICT)
    
    #laptime = round((time.time() - lasttime), 2)
    #print("time: " + str(laptime))
    n_boxes = len(data['text'])
    
    frame = cv2.rectangle(frame, (current_dimensions[2], current_dimensions[0]), (current_dimensions[3], current_dimensions[1]), (255, 255, 255), 2)
    for i in range(n_boxes):
        if int(float(data['conf'][i])) > 50:
            (text, x, y, w, h) = (data['text'][i], data['left'][i], data['top'][i], data['width'][i], data['height'][i])
            if text and text.strip() != "":
                reading += (text)
                frame = cv2.rectangle(frame, (x + current_dimensions[2], y + current_dimensions[0]), (x + w + current_dimensions[2], y + h + current_dimensions[0]), (0, 255, 0), 2)
                frame = cv2.putText(frame, text, (x + current_dimensions[2], y - 10 + current_dimensions[0]), cv2.FONT_HERSHEY_PLAIN, 1, (0, 0, 255), 2)
    #print(reading)
    #Display the resulting frame
    cv2.startWindowThread()
    cv2.namedWindow("frame")
    cv2.imshow("frame", frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
# When everything done, release the capture
cap.release()
cv2.destroyAllWindows()
 