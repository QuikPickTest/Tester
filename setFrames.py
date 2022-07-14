from pynput import mouse
import cv2
import pytesseract
from pytesseract import Output
import time
from time import sleep
import threading

wind_x = 0
wind_y = 0
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
cap.set(cv2.CAP_PROP_FPS, 60)

num_stage = input("Input number of stages: ")
rects = []
clicks = 0
first = True


def on_click(x,y,button,pressed):
    global rects, clicks, first, wind_x, wind_y
    if pressed:
        if(not first):
            print("Clicked at: " + str(x) + ':' + str(y))
            x1 = x
            y1 = y-50
            print(x1/2,y1)
            rects.append(str(x1) + ':' + str(y1))
            clicks+=1
        first = False
    elif not pressed:
        return False

def video():
    global clicks, num_stage
    while(clicks < int(num_stage)*2):

        ret, frame = cap.read() # Capture frame-by-frame

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        ret, bw = cv2.threshold(gray, 150,255, cv2.THRESH_BINARY)

        d = pytesseract.image_to_data(bw, lang = 'eng', output_type=Output.DICT)

        n_boxes = len(d['text'])

        for i in range(n_boxes):
            if int(float(d['conf'][i])) > 50:
                (text, x, y, w, h) = (d['text'][i], d['left'][i], d['top'][i], d['width'][i], d['height'][i])
                # don't show empty text
                if text and text.strip() != "":
                    frame = cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    frame = cv2.putText(frame, text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)


        cv2.startWindowThread()
        cv2.namedWindow("frame")
        cv2.moveWindow("frame", wind_x, wind_y)
        cv2.imshow("frame", frame)
        cv2.waitKey(1)
    
    cv2.destroyAllWindows()
    return True

def Mouse():
    global clicks, num_stage
    alert = True
    while(clicks < int(num_stage)*2):
    
        if(clicks % 2 == 0):
            print('SCREEN ' + str(int(clicks/2 + 1)) + ". Click on top left then bottom right of desired area of screen.")
        
        with mouse.Listener(on_click = on_click) as listener:
            listener.join()
    print(rects)
    return True

if __name__ == "__main__":
    # creating thread
    t1 = threading.Thread(target=Mouse)
    t2 = threading.Thread(target=video)

    # starting thread 1
    t1.start()
    # starting thread 2
    t2.start()
  
    # wait until thread 1 is completely executed
    t1.join()
    # wait until thread 2 is completely executed
    t2.join()
    
    with open('pos.txt', 'w') as f:

        for i in range(int(num_stage)):
            f.write(str(rects[2*i]) + ',' + str(rects[(2*i) + 1]) + '\n')

    # both threads completely executed
    print("Done!")