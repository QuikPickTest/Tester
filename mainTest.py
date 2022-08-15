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
import paramiko
import nidaqmx
from nidaqmx.constants import TerminalConfiguration
import threading
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import subprocess
GPIO.setwarnings(False)

# Start google drive
def start_Google_drive():
    global drive
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()
    drive = GoogleDrive(gauth)
    
# Function to start vending ssh
def start_ssh_server():
    global client,ssh_command
    ssh_command = "tail -n 200 /data2/log/yitunnel-all.log" # Command to run on cooler computer - looks at past 200 lines in log
    host = "192.168.2.100"
    username = "sandstar"
    password = "Xe08v0Zy"
    port = 45673
    client = paramiko.client.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=username, password=password, port = port)

# Start camera
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
cap.set(cv2.CAP_PROP_FPS, 30)

# Initialize Relays
TAP = 3 # Tapper
COOLER = 4 # Cooler power
INSERT_A = 20 # Card insert actuator
INSERT_B = 26
NFC_A = 22 # NFC actuator
NFC_B = 27
STEP_POWER = 17 # Power for stepper driver
DIR = 23   # Direction GPIO Pin
STEP = 24  # Step GPIO Pin
CW = 1     # Clockwise Rotation
CCW = 0    # Counterclockwise Rotation

GPIO.setmode(GPIO.BCM)
GPIO.setup(TAP, GPIO.OUT)
GPIO.setup(COOLER, GPIO.OUT)
GPIO.setup(STEP_POWER, GPIO.OUT)
GPIO.setup(INSERT_A, GPIO.OUT)
GPIO.setup(INSERT_B, GPIO.OUT)
GPIO.setup(NFC_A, GPIO.OUT)
GPIO.setup(NFC_B, GPIO.OUT)
GPIO.setup(DIR, GPIO.OUT)
GPIO.setup(STEP, GPIO.OUT)
# Need to set them all high because they default as on (which is GPIO.LOW)
GPIO.output(TAP, GPIO.HIGH) ## HIGH MEANS LOW!!!
GPIO.output(COOLER, GPIO.HIGH)
GPIO.output(INSERT_A, GPIO.HIGH)
GPIO.output(INSERT_B, GPIO.HIGH)
GPIO.setup(NFC_A, GPIO.HIGH)
GPIO.setup(NFC_B, GPIO.HIGH)

# Global variables and arrays
quitting = False
time_name = ''
trial_amount = ''
color_thresh = 150
ocr_timeout = 18
fail_amount = 4
time_door_open = 5
video_id = 0
drive_on = False
drive = 0
ssh_on = False
daq_on = False
commands = []
successes = 0
trial = 0
last_error = 0
daq_log = []
ocr_log = []
ssh_log = []
frame_log = []
daq_correct = True
ssh_correct = True
ocr_correct = True
succ_rate = 0
current_key = ''
current_dimensions = [0,int(cap.get(4)),0,int(cap.get(4))]
current_reading = ''


# Read instruction file and put it into 'commands' list
def parse_instruct_file(path = 'instruct.txt'):
    global commands
    if(path == ''):
        path = 'instruct.txt'
    with open(path, 'r') as f:
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

# Read settings file and set all variables to specified values
def read_settings():
    global color_thresh,ocr_timeout,fail_amount,video_id
    with open('settings.txt', 'r') as f:
        lines = f.readlines()
        for line in lines:
            line = line.split()
            if(line[0] == 'color_thresh'):
                color_thresh = int(line[2])
            elif(line[0] == 'ocr_timeout'):
                ocr_timeout = int(line[2])
            elif(line[0] == 'fail_amount'):
                fail_amount = int(line[2])
            elif(line[0] == 'time_door_open'):
                time_door_open = int(line[2])
            elif(line[0] == 'video_id'):
                video_id = int(line[2])


# Function for reading words on current screen and drawing it onto frame
def scan():
    global quitting,color_thresh,current_key,current_dimensions,frame_log,current_reading,cap
    while(True):
        # Quit program if 'x' key is pressed or quitting varible true
        if(quitting == True):
            break
        if(keyboard.is_pressed('x')):
            print('quit from scan')
            quitting = True
            cap.release()
            cv2.destroyAllWindows()
            quit_run()

        ret, frame = cap.read() # Capture frame-by-frame
        reading = ""
      
        cropFrame = frame[int(current_dimensions[0]):int(current_dimensions[1]),int(current_dimensions[2]):int(current_dimensions[3])]
        gray = cv2.cvtColor(cropFrame, cv2.COLOR_BGR2GRAY) # convert to grayscale
        ret, bw = cv2.threshold(gray,color_thresh, 255, cv2.THRESH_BINARY) # convert text to white and everything else black (beige/white = 225)

        data = pytesseract.image_to_data(bw, lang = 'eng', nice = 0, output_type=Output.DICT) # Actual function to do OCR
        
        frame = cv2.putText(frame, ('SEARCHING FOR: "' + current_key + '"'), (10,20), cv2.FONT_HERSHEY_PLAIN, 1.2,(0, 0, 255), 2)
        # Drawing portion where OCR is scanning
        frame = cv2.rectangle(frame, (int(current_dimensions[2]), int(current_dimensions[0])), (int(current_dimensions[3]), int(current_dimensions[1])), (255, 255, 255), 2)
        # Drawing words and word boxes onto frame
        n_boxes = len(data['text'])
        for i in range(n_boxes):
            if int(float(data['conf'][i])) > 60:
                (text, x, y, w, h) = (data['text'][i], data['left'][i], data['top'][i], data['width'][i], data['height'][i])
                if text and text.strip() != "":
                    reading += (text)
                    frame = cv2.rectangle(frame, (x + int(current_dimensions[2]), y + int(current_dimensions[0])), (x + w + int(current_dimensions[2]), y + h + int(current_dimensions[0])), (0, 255, 0), 2)
                    frame = cv2.putText(frame, text, (x + int(current_dimensions[2]), y - 10 + int(current_dimensions[0])), cv2.FONT_HERSHEY_PLAIN, 1, (0, 0, 255), 2)
        
        current_reading = reading.lower()
        frame_log.append(frame)

        cv2.startWindowThread()
        cv2.namedWindow("frame")
        cv2.imshow("frame", frame)
        cv2.waitKey(1)
        #sleep(.2)

    cap.release()
    cv2.destroyAllWindows()
    return True

# Function for tapping screen
def tap():
    print("TAPPING...")
    GPIO.output(TAP, GPIO.LOW)
    sleep(.2)
    GPIO.output(TAP, GPIO.HIGH)
            
# Function for opening door
def open_door():
    global time_door_open
    print("OPENING DOOR...")
    GPIO.output(DIR, CW)
    start = time.time()
    while((time.time()-start) < time_door_open):
        GPIO.output(STEP, GPIO.HIGH)
        sleep(.0001)
        GPIO.output(STEP, GPIO.LOW)
    return True

# Function for closing door
def close_door():
    global current_dimensions,current_key,current_reading,time_door_open
    print("CLOSING DOOR...")
    GPIO.output(DIR, CCW)
    current_dimensions = [250,300,200,350]
    start = time.time()
    while((time.time()-start) < time_door_open):
        GPIO.output(STEP, GPIO.HIGH)
        sleep(.0001)
        GPIO.output(STEP, GPIO.LOW)
        if('done' in current_reading): # If 'done' is on screen then automatically stop closing door
            break
    return True

# Function to insert card
def insert_in():
    print("INSERTING CARD...")
    GPIO.output(INSERT_A, GPIO.LOW)
    GPIO.output(INSERT_B, GPIO.HIGH)
    sleep(2)
    GPIO.output(INSERT_A, GPIO.HIGH)

# Function to remove card
def insert_out():
    print("RETRACTING CARD...")
    GPIO.output(INSERT_A, GPIO.HIGH)
    GPIO.output(INSERT_B, GPIO.LOW)
    sleep(2)
    GPIO.output(INSERT_B, GPIO.HIGH)

# Function to put NFC above reader
def NFC_on():
    print("PUTTING NFC ON READER...")
    GPIO.output(NFC_A, GPIO.LOW)
    GPIO.output(NFC_B, GPIO.HIGH)
    sleep(2)
    GPIO.output(NFC_A, GPIO.HIGH)

# Function to remove NFC from reader
def NFC_off():
    print("TAKING NFC OFF READER...")
    GPIO.output(NFC_A, GPIO.HIGH)
    GPIO.output(NFC_B, GPIO.LOW)
    sleep(2)
    GPIO.output(NFC_B, GPIO.HIGH)

# Function for turning on and off the cooler 
def restart_cooler(ocr_key):
    global current_reading,current_dimensions,current_key,ssh_on
    current_key = 'TAP'
    print('REBOOTING COOLER...')
    log = open("error_log.txt", "a")
    log.write('TRIAL FAILED 4 TIMES IN A ROW. RESTARTING COOLER')
    log.close()
    GPIO.output(COOLER, GPIO.LOW)
    sleep(5)
    GPIO.output(COOLER, GPIO.HIGH)
    start = time.time()
    current_dimensions = [250,400,100,350]
    while((time.time()-start) < 100):
        if(ocr_key in current_reading):
            print("OCR KEY FOUND. COOLER REBOOTED")
            break
    if(ssh_on):
        start_ssh_server()
        
# Function to check if specified key is in the vending ssh log and returns log
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

# Function for reading daq channel for set amount of seconds and checking if it surpassed given threshhold
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

# Function for terminating program
def quit_run():
    global trial,succ_rate,cap,trial_amount,quitting,drive_on,ssh_on,drive,time_name,folder_path
    quitting = True
    print('------------------------------------------------------------------------------')
    print('TERMINATING TESTING...')

    with open("error_log.txt", "a") as log:
        log.write('\n-------------------------------------------------------------------------------')
        log.write('\nTEST TERMINATED AT TRIAL ' + str(trial) + '/' + trial_amount + ': [' + str(time.strftime("%Y/%m/%d-%H:%M:%S")) + ']')
        log.write('\nSUCCESS RATE: ' + str(succ_rate) + '%' )
    
    
    if(drive_on):
        shutil.move('error_log.txt', time_name) # move error log to folder where error videos are stored
        
        # Create folder in google drive
        folder = drive.CreateFile({'title': time_name, 'mimeType': 'application/vnd.google-apps.folder'})
        folder.Upload()
        id = folder['id']
        # Move error log and all error videos to google drive folder
        for filename in os.listdir(time_name):
            f = os.path.join(time_name, filename)
            f1 = drive.CreateFile({'title': filename, "parents": [{"id": id, "kind": "drive#childList"}]})
            f1.SetContentFile(f)
            f1.Upload()

    if(ssh_on):
        client.close()
    GPIO.output(STEP_POWER, GPIO.HIGH)
    exit()

# Function for writing error to log file
def write_error(msg, ocr_log = [], daq_log = [], ssh_log = '', frame = []):
    global folder_id, trial, trial_amount
    err_time = str(time.strftime("%Y/%m/%d-%H:%M:%S"))
    log = open("error_log.txt", "a", encoding="utf-8")
    log.write('\n\n-------------------------------------------------------------------------------')
    log.write('\nERROR ON TRIAL ' + str(trial) + '/' + trial_amount)
    log.write('\nTIMESTAMP: [' + err_time + ']\n')
    log.write(msg)

    # Write everything the OCR was reading during error if there was any readings
    if(ocr_log):
        log.write('\n\nOCR READINGS:')
        for line in ocr_log:
            log.write('\n   READING: "' + line + '"')
    # Write everything the DAQ was reading during error if there was any readings
    if(daq_log):
        log.write('\n\nDAQ READINGS:')
        for line in daq_log:
            log.write('\n   READING: "' + str(line) + '"')
    log.close()


def do_action(action, ocr_flag, ocr_crop, ocr_key):
    global quitting,ocr_correct,ocr_log,current_reading,current_dimensions,current_key
    
    # Handler for each type of action
    if(action == 'tap'):
        tap()
    elif(action == 'open_door'):
        open_door()
    elif(action == 'close_door'):
        close_door()
    elif(action == 'insert_in'):
        insert_in()
    elif(action == 'insert_out'):
        insert_out()
    elif(action == 'NFC_on'):
        NFC_on()
    elif(action == 'NFC_off'):
        NFC_off()

    # If OCR flag is 1 then check for confirmation key on screen after action is done
    if(ocr_flag == 1):
        ocr_log = []
        ocr_correct = False
        start = time.time()

        while((time.time()-start) < 5):
            if(quitting == True):
                exit()
            if(keyboard.is_pressed('x')):
                quitting = True
                quit_run()

            ocr_log.append(current_reading)
            current_dimensions = ocr_crop
            current_key = ocr_key
            if(ocr_key in current_reading):
                print('OCR CONFIRMATION KEY "' + ocr_key + '" FOUND')
                ocr_correct = True
                return True
            sleep(.1)
    # If OCR flag is 0 then move on
    else: 
        ocr_correct = True
        return True

# Function to run trial
def process_command(command):
    global quitting,trial,ocr_correct,ssh_correct,daq_correct,ocr_log,daq_log,ssh_log,current_reading,current_key,current_dimensions,ssh_on,daq_on,ocr_timeout

    # Assigning correct values to all variables
    current_key = command[0][0][1:-1]
    current_dimensions =  command[0][1][1:-1].split(':')
    action = command[1][0]
    ocr_key = command[2][0][1:-1]
    ocr_flag = int(command[2][1])
    ocr_crop = [0,0,0,0]
    if(ocr_key != 'NONE'):
        ocr_crop = command[2][2][1:-1].split(':')
    ssh_key = command[3][0][1:-1]    
    ssh_flag = int(command[3][1])
    daq_flag = int(command[4][1])
    daq_channel = command[4][0]
    daq_compare = command[4][0]
    daq_thresh = command[4][0]
    if(command[4][0] != "'NONE'"):
        daq_channel = command[4][0].split(':')[0]
        daq_compare = command[4][0].split(':')[1][0]
        daq_thresh = command[4][0].split(':')[1][1:]
    
    starttime = time.time()
    ocr_log =[]
    frame = 0

    # Look for OCR keyword to start command
    while(True):

        # Quit program if quitting variable true
        if(quitting == True):
            exit()
        if(keyboard.is_pressed('x')):
            quitting = True
            quit_run()

        print('   READING: "' + current_reading + '"')
        ocr_log.append(current_reading)
        
        # Break when the ocr keyword is detected on the current screen
        if(current_key in current_reading):
            print('KEYWORD "' + current_key + '" FOUND')
            break
        
        # Skip to next screen and send error report if ocr key isn't detected within set time
        if((time.time()-starttime) > ocr_timeout):
            msg = 'ERROR: TOOK TOO LONG TO FIND KEYWORD "' + current_key + '" TO START COMMAND, SKIPPING TO NEXT COMMAND'
            print(msg)

            global last_error
            if(trial != last_error): # Make sure to only write error if its the first error of trial
                write_error(msg, ocr_log = ocr_log)
                last_error = trial
                if(action == 'close_door'):
                    close_door()
            return False
        sleep(.1)
    
    # Attemp to do command after ocr key was found
    attempt = 0
    while(True):
        if(quitting == True):
            exit()
        attempt += 1
        print('ATTEMPT ' + str(attempt) + ':')

        # Start seperate threads for action, reading daq, and reading ssh so they run concurrently
        t1 = threading.Thread(target=do_action, args=(action,ocr_flag,ocr_crop,ocr_key))
        t1.start()
        t1.join()

        if(ssh_on):
            t2 = threading.Thread(target=read_daq, args=(4,daq_channel,daq_thresh,daq_compare))
            t2.start()
            t2.join()
        if(daq_on):
            t3 = threading.Thread(target=read_ssh, args=(ssh_key,))
            t3.start()
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
            print("DAQ ERROR: DID NOT PASS THRESHHOLD: " + daq_channel + ':' + daq_compare + daq_thresh)
            msg += ('ERROR: DAQ DID NOT REACH DESIRED THRESHHOLD: ' + daq_channel + ':' + daq_compare + daq_thresh + '\n')
            if(daq_flag == 1):
                daq_pass = False
        if(ssh_correct == False):
            print('SSH ERROR: FAILED TO FIND SSH KEY: "' + ssh_key + '"')
            msg += ('ERROR: FAILED TO FIND SSH KEY: "' + ssh_key + '"\n')
            if(ssh_flag == 1):
                ssh_pass = False
        msg += ('[ATTEMPT ' + str(attempt) + ']\n')

        # If OCR, DAQ, and ssh pass then mark screen as success 
        if(ocr_pass and daq_pass and ssh_pass):
            return True
        else:
            write_error(msg = msg, ocr_log = ocr_log, daq_log = daq_log)
            if(attempt == 2):
                print('COMMAND FAILED TWICE. SKIPPING TO NEXT SCREEN')
                if(action == 'close_door'):
                    close_door()
                return False 
            else:
                print('ALL FLAGGED TESTS DID NOT PASS. RETRYING COMMAND')
       

##------------------ MAIN LOOP --------------------
def run(trial_amount):
    global trial,fail_amount,frame_log,commands,successes,folder_path,succ_rate,current_key,start,time_name
    repeat_fails = 0
    while(trial < int(trial_amount)):
        trial += 1
        correct = 0
        frame_log = []
        print('-----------------------------------')
        print('Trial ' + str(trial) + '/' + trial_amount + ':')
        print('-----------------------------------')
        
        for i in range(len(commands)):
            command = commands[i]
            current_key = command[0][0]
            print('SCANNING FOR: ' + command[0][0] + ' (SCREEN ' + str(commands.index(command) + 1) + ')') 
            if(process_command(command) == True):
                correct += 1
        
        # If all commands are successful count trial as success
        suc = 'FAILED'
        if(correct == len(commands)):
            successes += 1
            suc = 'SUCCESSFUL'
            repeat_fails = 0
        
        # If trial was a fail then upload full video of trial
        else:
            if(drive_on):
                vid_path = os.path.join(time_name,('Trial_' + str(trial) + '.avi'))
                res = cv2.VideoWriter(vid_path, cv2.VideoWriter_fourcc(*'MJPG'), 8, (640,480))
                for fr in frame_log:
                    res.write(fr)
                res.release()
            repeat_fails += 1
        
        succ_rate = (successes/trial)*100
        print('TRIAL ' + str(trial) + '/' + trial_amount + ' COMPLETE: ' + suc)
        print('TIME ELAPSED: ' + str(time.time()-start))
        print('SUCCESS RATE: ' + str(succ_rate) + '%')

        # If trials fail 4 times in a row then restart cooler
        if(repeat_fails == fail_amount):
            restart_cooler(ocr_key = 'TAP')
        if(repeat_fails == fail_amount+2):
            msg = 'FAILED 2 TIMES AFTER REBOOT. MANUALLY TERMINATING...'
            print(msg)
            write_error(msg = msg)
            break

    quit_run()


def main():
    global time_name,drive_on,ssh_on,daq_on,folder_path,start,trial_amount
    read_settings()
    path = input("Input instruction file path: ")
    parse_instruct_file(path)

    # User chooses wether to save log and serror videos to drive 
    save_inp = input('Save error log and videos to drive?(y/n): ')
    ssh_inp = input('Read vending log?(y/n): ')
    daq_inp = input('Read DAQ?(y/n): ')
    trial_amount = input('Input how many trials to run: ')

    if(ssh_inp == 'y'):
        ssh_on = True
        start_ssh_server()

    if(daq_inp == 'y'):
        daq_on = True

    # Initialize starting time
    start = time.time()
    time_name = str(time.strftime("%Y_%m_%d-%H-%M-%S"))
    if(save_inp == 'y'):
        drive_on = True
        #folder_path = os.path.join("D:/ErrorLog/", time_name)
        os.mkdir(time_name, mode = 0o777)
        start_Google_drive()

    # Wipe error log text file
    log = open("error_log.txt", "w")
    log.write("TEST STARTED AT: [" + str(time.strftime("%Y/%m/%d-%H:%M:%S")) + ']')
    log.close()

    # Run program and OCR concurrently
    t1 = threading.Thread(target=run, args = (trial_amount,))
    t2 = threading.Thread(target=scan)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

if __name__ == "__main__":
    main()