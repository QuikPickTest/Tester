#port 4 22 6 26
import cv2
import sys
import os
import shutil
import pytesseract
import keyboard
from pytesseract import Output
import time
from time import sleep
import RTk.GPIO as GPIO
from pydrive.drive import GoogleDrive
from pydrive.auth import GoogleAuth
import os
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import paramiko
import nidaqmx
from nidaqmx.constants import TerminalConfiguration
import threading
GPIO.setwarnings(False)


# Initialize starting time
start = time.time()
time_name = str(time.strftime("%Y%m%d-%H%M%S"))

# Vending server information
ssh_command = "tail -n 200 /data2/log/yitunnel-all.log"
host = "192.168.2.100"
username = "sandstar"
password = "Xe08v0Zy"
port = 45673
client = paramiko.client.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(host, username=username, password=password, port = port)

# Setting up new folder to store Error log and videos
inp = input('Save error log and videos to drive?(y/n): ')
drive_on = False
if(inp == 'y'):
    drive_on = True
    folder_path = os.path.join("D:/ErrorLog/", time_name)
    os.mkdir(folder_path)

# Read instruction files
commands = []
pos = []
with open('instruct.txt', 'r') as f:
    lines = f.readlines()
    for line in lines:
        if(line[-1] == '\n'):
            line = line[:-1]
        words = line.split('|')
        temp = []
        for w in words:        
            coms = w.split(',')
            temp.append(coms)
        commands.append(temp)
with open('pos.txt', 'r') as f:
    lines = f.readlines()
    for line in lines:
        pos.append(line.split(','))

# Wipe error log text file
log = open("error_log.txt", "w")
log.write("TEST STARTED AT: [" + time_name + ']')
log.close()

# Initialize Relays
TAP = 4
DOOR_A = 6
DOOR_B = 26
GPIO.setmode(GPIO.BCM)
GPIO.setup(TAP, GPIO.OUT)
GPIO.setup(DOOR_A, GPIO.OUT)
GPIO.setup(DOOR_B, GPIO.OUT)

# Start camera
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
cap.set(cv2.CAP_PROP_FPS, 60)

successes = 0
trial = 0
last_error = 0
daq_log = []
ocr_log = []
ssh_log = []
frame_log = []
daq_correct = False
ssh_correct = False
ocr_correct = False
succ_rate = 0

# Function for just tapping screen and not checking if tap worked
def tap():
    global cap
    cap.release()
    print("TAPPING...")
    GPIO.output(TAP, GPIO.HIGH)
    sleep(.2)
    GPIO.output(TAP, GPIO.LOW)
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_FPS, 60)

# Function for tapping screen and waiting to see if tap worked
def tap_and_wait(key, dimensions):
    tap()
    s = time.time()
    taps = 1
    readings = []

    while(True):

        # Quit program if 'x' key is pressed
        if(keyboard.is_pressed('x')):
            quit_run()

        if((time.time()-s) > 6):   
            if(taps == 2):
                print("TAPPED TOO MANY TIMES")
                return False,frame,readings
            tap()
            taps+=1
            s = time.time()

        text,frame = scan(key, dimensions)
        readings.append(text)

        if(key in text):
            print('TAP SUCCESSFUL')
            return True,frame, readings

            

# Functions for opening and closing door
def open_door(sec,key):
    global frame_log,ocr_log
    print("OPENING DOOR...")
    start = time.time()
    while((time.time()- start) < sec):
        GPIO.output(DOOR_A, GPIO.HIGH)
        GPIO.output(DOOR_B, GPIO.LOW)
        reading,frame = scan(ocr_key,[220,350,120,400])
        frame_log.append(frame)
        ocr_log.append(reading)
    GPIO.output(DOOR_A, GPIO.LOW)
    GPIO.output(DOOR_B, GPIO.LOW)
    return True

def close_door(sec,key):
    global frame_log,ocr_log
    print("OPENING DOOR...")
    start = time.time()
    while((time.time()- start) < sec):
        GPIO.output(DOOR_A, GPIO.LOW)
        GPIO.output(DOOR_B, GPIO.HIGH)
        reading,frame = scan(ocr_key,[220,350,120,400])
        frame_log.append(frame)
        ocr_log.append(reading)
    GPIO.output(DOOR_A, GPIO.LOW)
    GPIO.output(DOOR_B, GPIO.LOW)
    return True

# Function to check if specified key is in the vending log
def read_ssh(key):
    global ssh_correct
    if(key == "NONE"):
        ssh_correct = True
        return True
    ssh_correct = False
    stdin, stdout, stderr = client.exec_command(ssh_command)
    res = stdout.read().decode()
    if(key in res):
        print('SSH CORRECT')
        ssh_correct = True
        return True,res
    return False,res

# Function for reading daq channel for set amount of seconds and checking if it surpassed threshhold
def read_daq(sec, channel, thresh, comparator):
    global daq_log, daq_correct
    #print(sec,channel,thresh,comparator)
    if(channel == "'NONE'"):
        daq_correct = True
        return True

    daq_correct = False
    daq_log = []
    start = time.time()
    address = "cDAQ1Mod1/" + channel
    task = nidaqmx.Task()
    task.ai_channels.add_ai_voltage_chan(address, terminal_config = TerminalConfiguration.RSE)
    while(time.time()-start < sec):
        data = task.read(number_of_samples_per_channel=1)[0]
        daq_log.append(data)
        if(comparator == '>'):
            if(data >= float(thresh)):
                print("DAQ CORRECT")
                daq_correct = True
                task.close()
                return True
        else:    
            if(data <= float(thresh)):
                print("DAQ CORRECT")
                daq_correct = True
                task.close()
                return True
    task.close()
    return False

# Check if door is closed and close it if its not
if(read_daq(3,'ai0',2.2,'>')):
    print('DOOR OPEN BEFORE TESTING STARTED: CLOSING DOOR...')
    GPIO.output(DOOR_A, GPIO.LOW)
    GPIO.output(DOOR_B, GPIO.HIGH)
    sleep(4)
    GPIO.output(DOOR_A, GPIO.LOW)
    GPIO.output(DOOR_B, GPIO.LOW)

# Function for when program is manually terminated
def quit_run():
    global trial,succ_rate
    print('------------------------------------------------------------------------------')
    print('TERMINATING TESTING...')

    with open("error_log.txt", "a") as log:
        log.write('\n-------------------------------------------------------------------------------')
        log.write('\nTEST TERMINATED AT TRIAL ' + str(trial) + ': [' + str(time.strftime("%Y%m%d-%H%M%S")) + ']')
        log.write('\nSUCCESS RATE: ' + str(succ_rate) + '%' )

    global drive_on
    if(drive_on):
        shutil.move('error_log.txt', folder_path)
    cap.release()
    cv2.destroyAllWindows()
    client.close()
    exit()

# Function for writing error to log file and uploading picture to Drive
def write_error(msg, ocr_log = [], daq_log = [], ssh_log = '', frame = []):
    global folder_id, commands, trial
    err_time = str(time.strftime("%Y%m%d-%H%M%S"))
    log = open("error_log.txt", "a", encoding="utf-8")
    log.write('\n\n-------------------------------------------------------------------------------')
    log.write('\nERROR ON TRIAL ' + str(trial))
    log.write('\nTIMESTAMP: [' + err_time + ']\n')
    log.write(msg)
    log.write('\n\nOCR READINGS:')

    for line in ocr_log:
        log.write('\n   READING: "' + line + '"')

    if(daq_log):
        log.write('\n\nDAQ READINGS:')
    for line in daq_log:
        log.write('\n   READING: "' + str(line) + '"')

    log.close()


# Function for parsing instructions and assigning correct values to all parameters
def assign(command, p):
    key = command[0][0][1:-1]
    action = command[1][0]
    ocr = command[2]
    ssh_log = command[3]
    window_y1, window_y2 =  p[0].split(':')
    window_x1, window_x2 =  p[1].split(':')
    dimensions = [int(window_y1), int(window_y2), int(window_x1), int(window_x2)]
    daq = command[4]
    
    return key,action,ocr,ssh_log,dimensions,daq

# Function for reading words on current screen and drawing it onto frame
def scan(key, dimensions):
    ret, frame = cap.read() # Capture frame-by-frame
    reading = ""

    # Determine what portion of screen to read
    cropFrame = frame[dimensions[0]:dimensions[1], dimensions[2]:dimensions[3]]
    gray = cv2.cvtColor(cropFrame, cv2.COLOR_BGR2GRAY) # convert to grayscale
    ret, bw = cv2.threshold(gray, 150,255, cv2.THRESH_BINARY) # convert text to black and everything else white

    #cv2.startWindowThread()
    #cv2.namedWindow("bw")
    #cv2.imshow('bw',bw)

    data = pytesseract.image_to_data(bw, lang = 'eng', nice = 0, output_type=Output.DICT)
    n_boxes = len(data['text'])

    frame = cv2.putText(frame, ('SEARCHING: "' + key + '"'), (10,20), cv2.FONT_HERSHEY_PLAIN, 1.2,(0, 0, 255), 2)
    frame = cv2.rectangle(frame, (dimensions[2], dimensions[0]), (dimensions[3], dimensions[1]), (255, 255, 255), 2)
    for i in range(n_boxes):
        if int(float(data['conf'][i])) > 50:
            (text, x, y, w, h) = (data['text'][i], data['left'][i], data['top'][i], data['width'][i], data['height'][i])
            if text and text.strip() != "":
                reading += (text)
                frame = cv2.rectangle(frame, (x + dimensions[2], y + dimensions[0]), (x + w + dimensions[2], y + h + dimensions[0]), (0, 255, 0), 2)
                frame = cv2.putText(frame, text, (x + dimensions[2], y - 10 + dimensions[0]), cv2.FONT_HERSHEY_PLAIN, 1, (0, 0, 255), 2)
    
    cv2.startWindowThread()
    cv2.namedWindow("frame")
    cv2.imshow("frame", frame)
    cv2.waitKey(1)
    #cv2.destroyAllWindows()
    return reading,frame

def do_action(action, ocr_flag, ocr_key, sec):
    global ocr_correct, ocr_log,frame_log
    # Handler for each type of action
    if(action == 'tap'):
        tap()

    elif(action == 'open_door'):
        open_door(4,"")

    elif(action == 'close_door'):
        close_door(4,"")
    
    #print('flag: ' + str(ocr_flag))
    if(ocr_flag == 1):
        ocr_log = []
        ocr_correct = False
        start = time.time()
        while((time.time()-start) < sec):
            reading,frame = scan(ocr_key,[220,350,120,400])
            frame_log.append(frame)
            ocr_log.append(reading)
            if(ocr_key in reading):
                print('OCR CONFIRMATION KEY "' + ocr_key + '" FOUND')
                ocr_correct = True
                return True
    else:
        ocr_correct = True
        return True
    return True

# Function to run trial
def process_command(command, p, trial):
    global ocr_correct,ssh_correct,daq_correct,ocr_log,daq_log,ssh_log,frame_log
    key,action,ocr,ssh_log,dimensions,daq = assign(command,p)

    ocr_flag = int(ocr[1])
    ocr_key = ocr[0][1:-1]
    ssh_flag = int(ssh_log[1])
    ssh_key = ssh_log[0][1:-1]
    daq_flag = int(daq[1])
    daq_channel = daq[0]
    daq_compare = daq[0]
    daq_thresh = daq[0]
    if(daq[0] != "'NONE'"):
        #print(daq[0].split(':'))
        daq_channel = daq[0].split(':')[0]
        daq_compare = daq[0].split(':')[1][0]
        daq_thresh = daq[0].split(':')[1][1:]

    starttime = time.time()
    ocr_log =[]
    frame = 0
    
    # Look for keyword to start command
    while(True):

        # Quit program if 'x' key is pressed
        if(keyboard.is_pressed('x')):
            quit_run()
        
        text,frame = scan(key, dimensions) # Read words on screen
        frame_log.append(frame)

        print('   READING: "' + text + '"')
        ocr_log.append(text)
        
        # Handler for when the ocr keyword is detected on the current screen
        if(key in text):
            print('KEYWORD "' + key + '" FOUND')
            break
        
        # Skip to next screen and send error report if ocr key isn't detected within set time
        if((time.time()-starttime) > 18):
            msg = 'ERROR: TOOK TOO LONG TO FIND KEYWORD "' + key + '" TO START COMMAND'
            print('ERROR: TOOK TOO LONG TO FIND KEYWORD "' + key + '" TO START COMMAND. SKIPPING TO NEXT COMMAND')
            if(action == 'close_door'):
                close_door(4,ocr_key)
            global last_error
            if(trial != last_error):
                write_error(msg, ocr_log = ocr_log)
                last_error = trial
            return False
    
    # Attemp to do command
    tries = 0
    while(True):
        tries += 1
        t1 = threading.Thread(target=do_action, args=(action,ocr_flag,ocr_key,4))
        t2 = threading.Thread(target=read_daq, args=(4,daq_channel,daq_thresh,daq_compare))
        t3 = threading.Thread(target=read_ssh, args=(ssh_key,))

        t1.start()
        t2.start()
        t3.start()
        t1.join()
        t2.join()
        t3.join()

        ocr_pass = True
        daq_pass = True
        ssh_pass = True

        msg = ''
        if(ocr_correct == False):
            print('OCR ERROR: FAILED TO FIND OCR KEY "' + ocr_key + '" AFTER ACTION')
            msg += ('ERROR: FAILED TO FIND OCR KEY "' + ocr_key + '" AFTER ACTION\n')
            if(ocr_flag == 1):
                ocr_pass = False
        if(daq_correct == False):
            print("DAQ ERROR: DID NOT PASS THRESHHOLD: " + daq[0])
            msg += ('ERROR: DAQ DID NOT REACH DESIRED THRESHHOLD: ' + daq[0] + '\n')
            if(daq_flag == 1):
                daq_pass = False
        if(ssh_correct == False):
            print('SSH ERROR: FAILED TO FIND SSH KEY: "' + ssh_key + '"')
            msg += ('ERROR: FAILED TO FIND SSH KEY: "' + ssh_key + '"\n')
            if(ssh_flag == 1):
                ssh_pass = False

        #print(ocr_pass, daq_pass, ssh_pass)
        if(ocr_pass and daq_pass and ssh_pass):
            return True
        else:
            write_error(msg = msg, ocr_log = ocr_log, daq_log = daq_log)
            if(tries == 3):
                print('COMMAND FAILED TWICE. SKIPPING TO NEXT SCREEN')
                return False 
            else:
                print('ALL FLAGGED TESTS DID NOT PASS. RETRYING COMMAND')
       

##------------------ MAIN LOOP --------------------
while(True):
    trial += 1
    correct = 0
    frame_log = []
    print('-----------------------------------')
    print('Trial ' + str(trial) + ':')
    print('-----------------------------------')
    
    for i in range(len(commands)):
        command = commands[i]
        p = pos[i]
        print('ON SCREEN ' + str(commands.index(command) + 1))
        print('SCANNING FOR: ' + command[0][0]) 
        
        if(process_command(command,p,trial) == True):
            correct += 1
    
    # If all commands are successful count trial as success
    suc = 'FAILED'
    if(correct == len(commands)):
        successes += 1
        suc = 'SUCCESSFUL'
    
    # If it was a fail then upload video of trial
    elif(drive_on):
        vid_path = os.path.join(folder_path,('Trial_' + str(trial) + '.avi'))
        res = cv2.VideoWriter(vid_path, 
                         cv2.VideoWriter_fourcc(*'MJPG'),
                         8, (640,480))
        for fr in frame_log:
            res.write(fr)
        res.release()

    succ_rate = (successes/trial)*100
    print('TRIAL ' + str(trial) + ' COMPLETE: ' + suc)
    print('TIME ELAPSED: ' + str(time.time()-start))
    print('SUCCESS RATE: ' + str(succ_rate) + '%')

# When trials complete, close everything
quit_run()
