import time
from time import sleep
import RTk.GPIO as GPIO

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(3, GPIO.OUT)
GPIO.setup(17, GPIO.OUT)
GPIO.setup(18, GPIO.OUT)

GPIO.output(3, GPIO.HIGH)
GPIO.output(17, GPIO.HIGH)
GPIO.output(18, GPIO.HIGH)



GPIO.output(3, GPIO.LOW)
sleep(.2)
GPIO.output(3, GPIO.HIGH)
sleep(2)
