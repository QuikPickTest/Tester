import time
from time import sleep
import RTk.GPIO as GPIO

DIR = 23   # Direction GPIO Pin
STEP = 24  # Step GPIO Pin
CW = 1     # Clockwise Rotation
CCW = 0    # Counterclockwise Rotation
SPR = 48   # Steps per Revolution (360 / 7.5)

GPIO.setmode(GPIO.BCM)
GPIO.setup(DIR, GPIO.OUT)
GPIO.setup(17, GPIO.OUT)
GPIO.setup(STEP, GPIO.OUT)
GPIO.output(DIR, CCW)
GPIO.output(17, GPIO.LOW)
step_count = SPR
delay = .001
start = time.time()

while((time.time()-start) < 5):
    GPIO.output(STEP, GPIO.HIGH)
    sleep(.0001)
    GPIO.output(STEP, GPIO.LOW)

GPIO.output(17, GPIO.HIGH)

GPIO.output(DIR, CW)
start = time.time()
while((time.time()-start) < 15):
    GPIO.output(STEP, GPIO.HIGH)
    sleep(.0001)
    GPIO.output(STEP, GPIO.LOW)