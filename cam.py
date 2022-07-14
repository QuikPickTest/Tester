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

#GPIO.output(6, GPIO.LOW)
#GPIO.output(26, GPIO.HIGH)
#sleep(5)
#GPIO.output(6, GPIO.LOW)
#GPIO.output(26, GPIO.LOW)
while True:

    if((time.time() - start) > 1000):
        cap.release()
        GPIO.output(4, GPIO.HIGH)
        sleep(.2)
        GPIO.output(4, GPIO.LOW)

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

    ret, frame = cap.read()# Capture frame-by-frame
    #print(ret)
    #frame = cv2.resize(frame, (350, 250), fx=0, fy=0, interpolation = cv2.INTER_AREA)
    frame = frame[310:350,200:350]
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    #cv2.imshow('gray', gray)
    ret, bw = cv2.threshold(gray, 140,255, cv2.THRESH_BINARY)
    cv2.startWindowThread()
    cv2.namedWindow("bw")
    cv2.moveWindow("bw", 100, 50)
    cv2.imshow("bw", bw)
    d = pytesseract.image_to_data(bw, lang = 'eng', output_type=Output.DICT)
    
    #laptime = round((time.time() - lasttime), 2)
    #print("time: " + str(laptime))
    n_boxes = len(d['text'])
    
    
    for i in range(n_boxes):
        if int(float(d['conf'][i])) > 50:
            (text, x, y, w, h) = (d['text'][i], d['left'][i], d['top'][i], d['width'][i], d['height'][i])
            # don't show empty text
            if text and text.strip() != "":
                print(text)
                #print(str(x), str(y), str(w), str(h))
                frame = cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                frame = cv2.putText(frame, text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
    
    #Display the resulting frame
    cv2.startWindowThread()
    cv2.namedWindow("frame")
    cv2.imshow("frame", frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
# When everything done, release the capture
cap.release()
cv2.destroyAllWindows()
 