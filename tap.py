import time
from time import sleep
import RTk.GPIO as GPIO

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(4, GPIO.OUT)

GPIO.output(4, GPIO.HIGH)
sleep(.2)
GPIO.output(4, GPIO.LOW)
