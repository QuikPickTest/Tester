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
GPIO.setwarnings(False)

# Function to start vending server
def start_ssh_server():
    global client,ssh_command
    ssh_command = "tail -n 200 /data2/log/yitunnel-all.log"
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
TAP = 3
COOLER = 4
DOOR_A = 17
DOOR_B = 18
GPIO.setmode(GPIO.BCM)
GPIO.setup(TAP, GPIO.OUT)
GPIO.setup(COOLER, GPIO.OUT)
GPIO.setup(DOOR_A, GPIO.OUT)
GPIO.setup(DOOR_B, GPIO.OUT)
GPIO.output(TAP, GPIO.HIGH)
GPIO.output(COOLER, GPIO.HIGH)
GPIO.output(DOOR_A, GPIO.HIGH)
GPIO.output(DOOR_B, GPIO.HIGH)

# Global variables and arrays
quitting = False
trial_amount = ''
drive_on = False
ssh_on = False
daq_on = False
commands = []
crops = []
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
current_key = ''
current_dimensions = [0,int(cap.get(4)),0,int(cap.get(4))]
current_reading = ''


# Read instruction and image crop files
def parse_instruct_file(path = 'instruct.txt'):
    global crops,commands
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
    with open('crops.txt', 'r') as f:
        lines = f.readlines()
        for line in lines:
            crops.append(line.split(','))


# Function for reading words on current screen and drawing it onto frame
def scan():
    global quitting,current_key,current_dimensions,frame_log,current_reading,cap
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
        # Crop frame
        cropFrame = frame[current_dimensions[0]:current_dimensions[1],current_dimensions[2]:current_dimensions[3]]
        gray = cv2.cvtColor(cropFrame, cv2.COLOR_BGR2GRAY) # convert to grayscale
        ret, bw = cv2.threshold(gray, 150,255, cv2.THRESH_BINARY) # convert text to black and everything else white
        #cv2.startWindowThread()
        #cv2.namedWindow("bw")
        #cv2.imshow('bw',bw)

        data = pytesseract.image_to_data(bw, lang = 'eng', nice = 0, output_type=Output.DICT)
        n_boxes = len(data['text'])

        frame = cv2.putText(frame, ('SEARCHING FOR: "' + current_key + '"'), (10,20), cv2.FONT_HERSHEY_PLAIN, 1.2,(0, 0, 255), 2)
        frame = cv2.rectangle(frame, (current_dimensions[2], current_dimensions[0]), (current_dimensions[3], current_dimensions[1]), (255, 255, 255), 2)
        for i in range(n_boxes):
            if int(float(data['conf'][i])) > 60:
                (text, x, y, w, h) = (data['text'][i], data['left'][i], data['top'][i], data['width'][i], data['height'][i])
                if text and text.strip() != "":
                    reading += (text)
                    frame = cv2.rectangle(frame, (x + current_dimensions[2], y + current_dimensions[0]), (x + w + current_dimensions[2], y + h + current_dimensions[0]), (0, 255, 0), 2)
                    frame = cv2.putText(frame, text, (x + current_dimensions[2], y - 10 + current_dimensions[0]), cv2.FONT_HERSHEY_PLAIN, 1, (0, 0, 255), 2)
        
        current_reading = reading
        frame_log.append(frame)

        cv2.startWindowThread()
        cv2.namedWindow("frame")
        cv2.imshow("frame", frame)
        cv2.waitKey(1)
        sleep(.5)

    cap.release()
    cv2.destroyAllWindows()
    return True

# Function for tapping screen
def tap():
    print("TAPPING...")
    GPIO.output(TAP, GPIO.LOW)
    sleep(.2)
    GPIO.output(TAP, GPIO.HIGH)
            
# Functions for opening and closing door
def open_door(sec = 4):
    print("OPENING DOOR...")
    start = time.time()
    while((time.time()-start) < sec):
        GPIO.output(DOOR_A, GPIO.LOW)
        GPIO.output(DOOR_B, GPIO.HIGH)
    GPIO.output(DOOR_A, GPIO.HIGH)
    GPIO.output(DOOR_B, GPIO.HIGH)
    return True

def close_door(sec = 4):
    print("CLOSING DOOR...")
    start = time.time()
    while((time.time()-start) < sec):
        GPIO.output(DOOR_A, GPIO.HIGH)
        GPIO.output(DOOR_B, GPIO.LOW)
    GPIO.output(DOOR_A, GPIO.HIGH)
    GPIO.output(DOOR_B, GPIO.HIGH)
    return True

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
    current_dimensions = [300,450,120,400]
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

# Check daq to see if door is closed and close it if its not
if(drive_on and read_daq(.5,'ai0',2.2,'>')):
    print('DOOR OPEN BEFORE TESTING STARTED: CLOSING DOOR...')
    GPIO.output(DOOR_A, GPIO.HIGH)
    GPIO.output(DOOR_B, GPIO.LOW)
    sleep(4)
    GPIO.output(DOOR_A, GPIO.HIGH)
    GPIO.output(DOOR_B, GPIO.HIGH)

# Function for terminating program
def quit_run():
    global trial,succ_rate,cap,trial_amount,quitting
    quitting = True
    print('------------------------------------------------------------------------------')
    print('TERMINATING TESTING...')

    with open("error_log.txt", "a") as log:
        log.write('\n-------------------------------------------------------------------------------')
        log.write('\nTEST TERMINATED AT TRIAL ' + str(trial) + '/' + trial_amount + ': [' + str(time.strftime("%Y/%m/%d-%H:%M:%S")) + ']')
        log.write('\nSUCCESS RATE: ' + str(succ_rate) + '%' )

    global drive_on
    if(drive_on):
        shutil.move('error_log.txt', folder_path)
    log.close()
    client.close()
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

    
    if(ocr_log):
        log.write('\n\nOCR READINGS:')
        for line in ocr_log:
            log.write('\n   READING: "' + line + '"')

    if(daq_log):
        log.write('\n\nDAQ READINGS:')
        for line in daq_log:
            log.write('\n   READING: "' + str(line) + '"')
    log.close()


# Function for parsing instructions and assigning correct values to all parameters
def assign(command, crop):
    global current_dimensions,current_key
    current_key = command[0][0][1:-1]
    action = command[1][0]
    ocr_flag = int(command[2][1])
    ocr_key = command[2][0][1:-1]
    ssh_flag = int(command[3][1])
    ssh_key = command[3][0][1:-1]
    daq_flag = int(command[4][1])
    daq_channel = command[4][0]
    daq_compare = command[4][0]
    daq_thresh = command[4][0]
    if(command[4][0] != "'NONE'"):
        daq_channel = command[4][0].split(':')[0]
        daq_compare = command[4][0].split(':')[1][0]
        daq_thresh = command[4][0].split(':')[1][1:]

    window_y1, window_y2 =  crop[0].split(':')
    window_x1, window_x2 =  crop[1].split(':')
    current_dimensions = [int(window_y1), int(window_y2), int(window_x1), int(window_x2)]

    return action,ocr_flag,ocr_key,ssh_flag,ssh_key,daq_flag,daq_channel,daq_compare,daq_thresh


def do_action(action, ocr_flag, ocr_key, sec):
    global quitting,ocr_correct, ocr_log, current_reading, current_dimensions, current_key
    # Handler for each type of action
    if(action == 'tap'):
        tap()

    elif(action == 'open_door'):
        open_door(4)

    elif(action == 'close_door'):
        close_door(4)
    
    # If OCR flag is 1 then check for confirmation key on screen after action is done
    if(ocr_flag == 1):
        ocr_log = []
        ocr_correct = False
        start = time.time()

        while((time.time()-start) < sec):
            if(quitting == True):
                exit()
            if(keyboard.is_pressed('x')):
                #quitting = True
                quit_run()

            ocr_log.append(current_reading)
            current_dimensions = [210,350,120,400]
            current_key = ocr_key
            if(ocr_key in current_reading):
                print('OCR CONFIRMATION KEY "' + ocr_key + '" FOUND')
                ocr_correct = True
                return True
            sleep(.1)
    else:
        ocr_correct = True
        return True
    return True

# Function to run trial
def process_command(command,crop):
    global quitting,trial,ocr_correct,ssh_correct,daq_correct,ocr_log,daq_log,ssh_log,current_reading,current_dimensions,ssh_on,daq_on

    action,ocr_flag,ocr_key,ssh_flag,ssh_key,daq_flag,daq_channel,daq_compare,daq_thresh = assign(command,crop)

    starttime = time.time()
    ocr_log =[]
    frame = 0
    
    # Look for ocr keyword to start command
    while(True):

        # Quit program if quitting variable true
        if(quitting == True):
            exit()

        print('   READING: "' + current_reading + '"')
        ocr_log.append(current_reading)
        
        # Handler for when the ocr keyword is detected on the current screen
        if(current_key in current_reading):
            print('KEYWORD "' + current_key + '" FOUND')
            break
        
        # Skip to next screen and send error report if ocr key isn't detected within set time
        if((time.time()-starttime) > 18):
            msg = 'ERROR: TOOK TOO LONG TO FIND KEYWORD "' + current_key + '" TO START COMMAND, SKIPPING TO NEXT COMMAND'
            print(msg)
            global last_error
            if(trial != last_error):
                write_error(msg, ocr_log = ocr_log)
                last_error = trial
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
        t1 = threading.Thread(target=do_action, args=(action,ocr_flag,ocr_key,4))

        if(ssh_on):
            t2 = threading.Thread(target=read_daq, args=(4,daq_channel,daq_thresh,daq_compare))
            t2.start()
            t2.join()
        if(daq_on):
            t3 = threading.Thread(target=read_ssh, args=(ssh_key,))
            t3.start
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

        if(ocr_pass and daq_pass and ssh_pass):
            return True
        else:
            write_error(msg = msg, ocr_log = ocr_log, daq_log = daq_log)
            if(attempt == 2):
                print('COMMAND FAILED TWICE. SKIPPING TO NEXT SCREEN')
                return False 
            else:
                print('ALL FLAGGED TESTS DID NOT PASS. RETRYING COMMAND')
       

##------------------ MAIN LOOP --------------------
def run(trial_amount):
    global trial,frame_log,commands,crops,successes,folder_path,succ_rate,current_key,start
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
            crop = crops[i]
            print('SCANNING FOR: ' + command[0][0] + ' (SCREEN ' + str(commands.index(command) + 1) + ')') 
            if(process_command(command,crop) == True):
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
                vid_path = os.path.join(folder_path,('Trial_' + str(trial) + '.avi'))
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
        if(repeat_fails == 4):
            restart_cooler(ocr_key = 'TAP')
        if(repeat_fails == 6):
            msg = 'FAILED 2 TIMES AFTER REBOOT. MANUALLY TERMINATING...'
            print(msg)
            write_error(msg = msg)
            break

    quit_run()


def main():
    global drive_on,ssh_on,daq_onfolder_path,start,trial_amount
    path = input("Input instruction file path: ")
    parse_instruct_file(path)

    # User chooses wether to save log and error videos to drive 
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
        folder_path = os.path.join("D:/ErrorLog/", time_name)
        os.mkdir(folder_path)
    

    # Wipe error log text file
    log = open("error_log.txt", "w")
    log.write("TEST STARTED AT: [" + str(time.strftime("%Y/%m/%d-%H:%M:%S")) + ']')
    log.close()


    # Run program and text detecter concurrently
    t1 = threading.Thread(target=run, args = (trial_amount,))
    t2 = threading.Thread(target=scan)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

if __name__ == "__main__":
    main()