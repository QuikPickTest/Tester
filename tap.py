import time
from time import sleep
import RTk.GPIO as GPIO

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(3, GPIO.OUT)
GPIO.setup(4, GPIO.OUT)
GPIO.setup(17, GPIO.OUT)
GPIO.setup(18, GPIO.OUT)
GPIO.setup(22, GPIO.OUT)
GPIO.setup(27, GPIO.OUT)
GPIO.setup(20, GPIO.OUT)
GPIO.setup(26, GPIO.OUT)

GPIO.output(3, GPIO.HIGH)
GPIO.output(4, GPIO.HIGH)
GPIO.output(17, GPIO.HIGH)
GPIO.output(18, GPIO.HIGH)
GPIO.output(22, GPIO.HIGH)
GPIO.output(27, GPIO.HIGH)
GPIO.output(20, GPIO.HIGH)
GPIO.output(26, GPIO.HIGH)


#GPIO.output(20, GPIO.HIGH)
#GPIO.output(26, GPIO.LOW)
#sleep(3)
#GPIO.output(20, GPIO.HIGH)
#GPIO.output(26, GPIO.HIGH)
#

#GPIO.output(17, GPIO.HIGH)
#sleep(10)
#GPIO.output(17, GPIO.HIGH)
GPIO.output(3, GPIO.LOW)
sleep(.2)
GPIO.output(3, GPIO.HIGH)

while(False):
    GPIO.output(20, GPIO.LOW)
    GPIO.output(26, GPIO.HIGH)
    GPIO.output(22, GPIO.LOW)
    GPIO.output(27, GPIO.HIGH)
    sleep(3)
    GPIO.output(20, GPIO.HIGH)
    GPIO.output(26, GPIO.LOW)
    GPIO.output(22, GPIO.HIGH)
    GPIO.output(27, GPIO.LOW)
    sleep(3)
