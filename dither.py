#<head></head>
#<body>
#<h2><center>This software is copyright 2018<br>
#Bill Cunning / CSoft Software
#</center>
#</h2>
#<h3>
#This software is licensed under the Creative Commons License and may be
#modified and shared as long as the terms of the license are followed
#</h3>
#<a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by-nc-sa/4.0/88x31.png" /></a><br />This work is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/">Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License</a>.
#</body>
#
#A big thank you to DonBoy from CloudyNights forums for all the testing
#and suggestions he has and continues to make!
#




import socket
import sys
import json
import threading
import os
from time import sleep

class GlobalVariables:
    is_guiding = 0
    localImageCounter = 0
    fakedImages = 0
    terminate = 0
    forceTerminate = 0
    isDithering = 0
    PHDThreadRunning = 0
    CaptureThreadRunning = 0
    startCaptureClicked = 0
    stopCaptureClicked = 0
    message = []
    doPhdDither = 0
    needs_unpausing = 0


    cmd_list = {}
    valid_commands = ["FC", "DE", "PA", "GS", "EX", "GA", "DD", "LS", "SD"]



GlobalVars = GlobalVariables
lock = threading.Lock()

#============================================================================



#===========================================================================
#    edit these values
#===========================================================================
#these need to be set for your specific setup
#total frames to take
GlobalVars.cmd_list["FC"] = 13
#dither ever DE frames
GlobalVars.cmd_list["DE"] = 5
#path to actual dither program
#Dither command line
GlobalVars.cmd_list["PA"] = 'c:/phddither/phd_dither.exe 1 true'
#path to config file
GlobalVars.cmd_list["CF"] = 'C:/Users/bill/Documents/sharpcapscripts/config.txt'
#stop when guiding stops .. if set to one .. otherwise will run till frameCount
#is reached or the stop button is pushed
GlobalVars.cmd_list["GS"] = 1
#if set to 0 use the phddither.exe application if set to 1, 2, or 3
#dither with phd directly at that level of dithereing (low medium high)
GlobalVars.cmd_list["DD"] = 2
#set to one if you are doing live stacking
#0 otherwise
GlobalVars.cmd_list["LS"] = 0
#wait one frame after we recieve settledone if set to one else
#start stacking as soon as we get the settle done
GlobalVars.cmd_list["SD"] = 0
#============================================================================
#============================================================================
#=========== from here downward is optional - if left as is it will use the
#=========== current SharpCap settings
#============================================================================
#if Use Current Settings (UC) is set to one it will use the current sharp
#cap settings
#if set to 0 will use the following values to reset the sharpcap settings
# and then use those
GlobalVars.cmd_list["UC"] = 1
#if UC is 0 and UF is one read the file config.txt for these values
GlobalVars.cmd_list["UF"] = 0
#if UC = 0 and UF = 0 use these default values
#exposure
GlobalVars.cmd_list["EX"] = 0.1
#gain
GlobalVars.cmd_list["GA"] = 50
#ColorSpace
GlobalVars.cmd_list["CS"] = "RAW16"
#output format
GlobalVars.cmd_list["OF"] = "FITS files (*.fits)"

#===========================================================================
#==========================================================================
# globals .. doesnt make me happy but it works :)

#for Testing without sharpcap use 0
USE_SHARP_CAP = 1

host = '127.0.0.1'
port = 4400
ditherport = 4300


#==========================================================================
#=========================================================================+
# stub out the calls to sharp cap
# pylint: disable=undefined-variable

def buildMessage(type,msg):
	message = {}
	message["type"] = type + ": "
	message["msg"] = msg
	return message


def sharpCapInitCapture(use_sharp_cap):

    GlobalVars.localImageCounter = 0
    GlobalVars.fakedImages = 0
    if use_sharp_cap:
        try:
            # _______setup capture Blue (limited , count, wait)
            SharpCap.SelectedCamera.CaptureConfig.CaptureLimitType = SharpCap.SelectedCamera.CaptureConfig.CaptureLimitType.FrameLimited
            #____________  make sharp cap think its a couple longer than we want . if they both shut down at the same time
            #____________  we get into a race condition
            SharpCap.SelectedCamera.CaptureConfig.CaptureLimitValue = GlobalVars.cmd_list["FC"] + 2
            SharpCap.SelectedCamera.CaptureConfig.CaptureSequenceCount = 1
            SharpCap.SelectedCamera.CaptureConfig.CaptureSequenceInterval = 0
        except:
        #this is fatal abort
            print "fatal error - restart sharpcap and select camera first"
            sys.exit()

def sharpCapIsCapturing(use_sharp_cap):

    if use_sharp_cap:
        return SharpCap.SelectedCamera.Capturing

    return True

def sharpCapGetImageCount(use_sharp_cap):

    if use_sharp_cap:
        return SharpCap.SelectedCamera.CapturedFrameCount
    else:
        GlobalVars.localImageCounter = GlobalVars.localImageCounter + 1
        if GlobalVars.localImageCounter > 10:
            GlobalVars.fakedImages = GlobalVars.fakedImages + 1
            GlobalVars.localImageCounter = 0
    return GlobalVars.fakedImages

def sharpCapToggleCameraPaused(use_sharp_cap, value):

    if use_sharp_cap:
        SharpCap.SelectedCamera.Paused = value



def sharpCapPrepareAndRun(use_sharp_cap):
    if use_sharp_cap:
        if not SharpCap.SelectedCamera.Capturing:
            #setMessage("STATUS: preparing capture \r\n")
            setMessage(buildMessage("STATUS", "preparing capture"))
            SharpCap.SelectedCamera.PrepareToCapture()
            SharpCap.SelectedCamera.RunCapture()
        else:
            if GlobalVars.needs_unpausing == 1:
                #setMessage("STATUS: resuming \r\n")
                setMessage(buildMessage("STATUS", "resuming"))
                SharpCap.SelectedCamera.Paused = False
                GlobalVars.needs_unpausing = 0
    else:
        if GlobalVars.needs_unpausing == 1:
            #setMessage("STATUS: resuming \r\n")
            setMessage(buildMessage("STATUS", "resuming"))
            GlobalVars.needs_unpausing = 0


def sharpCapStopCapture(use_sharp_cap):
    if use_sharp_cap:
        if SharpCap.SelectedCamera.Capturing:
            SharpCap.SelectedCamera.StopCapture()


#===========================================================================
#===========================================================================
#this is the sharp cap thread if live stacking
def threaded_livestack():

    GlobalVars.CaptureThreadRunning = 1

    last_total_count = 0
    total_count = 0
    dither_count = 0
    GlobalVars.terminate = 0
    waitoneframe = 0

    last_total_count = SharpCap.SelectedCamera.CapturedFrameCount

    #setMessage("STATUS: live capture runninig \r\n")
    setMessage(buildMessage("STATUS", "live capture running"))
    while GlobalVars.forceTerminate == 0:
        print "in live capture loop"
        setMessage(buildMessage("DEBUG", "in live capture loop"))
        sleep(2)

        total_count = SharpCap.SelectedCamera.CapturedFrameCount
        

        if GlobalVars.isDithering == 1 and GlobalVars.needs_unpausing == 1:
            waitoneframe = total_count
            last_total_count = total_count
        else:
            if GlobalVars.needs_unpausing == 0:
                dither_count = total_count - last_total_count

        
        setMessage(buildMessage("DEBUG", "dither count " + str(dither_count)))
        
		
        if GlobalVars.isDithering == 0 and GlobalVars.needs_unpausing == 1:
            
            if GlobalVars.cmd_list["SD"] == 1:
                if total_count > waitoneframe:
                    SharpCap.LiveStacking.Parameters.Paused = False
                    GlobalVars.needs_unpausing = 0
                    last_total_count = total_count
            else:
                SharpCap.LiveStacking.Parameters.Paused = False
                GlobalVars.needs_unpausing = 0
                last_total_count = total_count

        
        if dither_count == GlobalVars.cmd_list["DE"] or dither_count > GlobalVars.cmd_list["DE"]:
            
            #setMessage("STATUS: dither start \r\n")
            setMessage(buildMessage("STATUS", "dither start"))
            SharpCap.LiveStacking.Parameters.Paused = True
            last_total_count = total_count

            dither_count = 0
            GlobalVars.isDithering = 1
            if GlobalVars.cmd_list["DD"] == 0:
                os.system(GlobalVars.cmd_list["PA"])
            else:
                #setMessage("STATUS: Sending dither command \r\n")
                setMessage(buildMessage("DEBUG", "sending dither command"))
                GlobalVars.doPhdDither = 1

            GlobalVars.needs_unpausing = 1

    GlobalVars.CaptureThreadRunning = 0
    #setMessage("STATUS: end live capture thread \r\n")
    setMessage(buildMessage("STATUS" , "end live capture thread"))

#==========================================================================
#=========================================================================+
# this function is the thread that deals with SharpCap standard capture
def threaded_send():

    lastTotalCount = 0

    sharpCapInitCapture(USE_SHARP_CAP)
    GlobalVars.CaptureThreadRunning = 1

    totalCount = 0
    ditherCount = 0
    GlobalVars.terminate = 0
    setMessage(buildMessage("STATUS", "Sharp cap standard thread"))
	
    while GlobalVars.terminate == 0:
        sleep(2)
        if GlobalVars.cmd_list["GS"] == 1:
            doCapture = GlobalVars.is_guiding
        else:
            doCapture = 1
        if GlobalVars.isDithering == 0 and doCapture == 0:
            #setMessage("STATUS: Waiting \r\n")
            setMessage(buildMessage("STATUS", "Waiting"))
        if GlobalVars.isDithering == 1:
            #setMessage("STATUS: Dithering \r\n")
            setMessage(buildMessage("STATUS","Dithering"))
        if GlobalVars.isDithering == 0 and doCapture == 1:
            #setMessage("STATUS: Capturing \r\n")
            setMessage(buildMessage("STATUS", "Capturing"))

        if GlobalVars.isDithering == 0:
            if doCapture == 1:

                if sharpCapIsCapturing(USE_SHARP_CAP):
                    totalCount = sharpCapGetImageCount(USE_SHARP_CAP)
                else:
                    totalCount = 0

                #setMessage("STATUS: Total Count = " + str(totalCount))
                setMessage(buildMessage("INFO", "Total Count = " + str(totalCount)))
                ditherCount = totalCount - lastTotalCount
                sharpCapPrepareAndRun(USE_SHARP_CAP)


                if ditherCount >= GlobalVars.cmd_list["DE"]:
                    #setMessage("STATUS: dither start \r\n")
                    setMessage(buildMessage("STATUS", "dither start"))
                    lastTotalCount = totalCount
                    sharpCapToggleCameraPaused(USE_SHARP_CAP, True)

                    ditherCount = 0
                    GlobalVars.isDithering = 1
                    if GlobalVars.cmd_list["DD"] == 0:
                        os.system(GlobalVars.cmd_list["PA"])
                    else:
                        #setMessage("STATUS: Sending dither command \r\n")
                        setMessage(buildMessage("DEBUG", "Sending dither command"))
                        GlobalVars.doPhdDither = 1

                    GlobalVars.needs_unpausing = 1

        if totalCount >= GlobalVars.cmd_list["FC"]:
            #setMessage("STATUS: exit capture thread on count \r\n")
            setMessage(buildMessage("STATUS","Exit capture thread on count"))
            GlobalVars.CaptureThreadRunning = 0
            sharpCapStopCapture(USE_SHARP_CAP)
            GlobalVars.forceTerminate = 1
            GlobalVars.terminate = 1
            exit()
        if GlobalVars.forceTerminate == 1:
            #setMessage("STATUS: exit capture thread \r\n")
            setMessage(buildMessage("STATUS", "Exit capture thread on forceterminate"))
            #SharpCap.SelectedCamera.Paused = True
            GlobalVars.CaptureThreadRunning = 0
            sharpCapStopCapture(USE_SHARP_CAP)
            exit()
        if GlobalVars.terminate == 1:
            #setMessage("STATUS: exit capture thread \r\n")
            setMessage(buildMessage("STATUS", "Exit capture thread on terminate"))
            sharpCapStopCapture(USE_SHARP_CAP)
            GlobalVars.CaptureThreadRunning = 0
            exit()
#===========================================================================
#===========================================================================
#===========================================================================
#===========================================================================
# this function is the thread that listens for phd updates

def threaded_listen():


    GlobalVars.PHDThreadRunning = 1


    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((host, port))
    except:
        print 'Unable to connect to phd server'
        exit()

    for l in s.makefile():
        m = json.loads(l)
        if 'Event' in m and m['Event'] != 'LoopingExposures':
            #setMessage("PHD: " + m['Event'] + "\r\n")
            eventtext = m['Event']
            setMessage(buildMessage("PHD", eventtext))
            if m['Event'] == 'StartGuiding':
                GlobalVars.is_guiding = 1
            if m['Event'] == 'GuideStep':
                GlobalVars.is_guiding = 1
            if m['Event'] == 'GuidingStopped':
                GlobalVars.is_guiding = 0
                if GlobalVars.cmd_list["GS"] == 1:
                    GlobalVars.terminate = 1
            if m['Event'] == 'GuidingDithered':
                GlobalVars.isDithering = 1
            if m['Event'] == 'SettleDone':
                GlobalVars.isDithering = 0
        sleep(1)
        if GlobalVars.forceTerminate == 1:
            print "exit phd loop"
            GlobalVars.PHDThreadRunning = 0
            exit()
        if GlobalVars.terminate == 1:
            print "phd loop exist"
            GlobalVars.PHDThreadRunning = 0
            exit()
#=============================================================================
#=============================================================================
# this is the function / thread that sends the dither command to phd
def phdDither():

    GlobalVars.terminate = 0
    phd_cmd_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        phd_cmd_socket.connect((host, ditherport))
    except:
        #setMessage('STATUS: Unable to connect to phd server')
        setMessage(buildMessage("ERROR",  "Unable to connect to phd server"))
        exit()
		
    setMessage(buildMessage("DEBUG", "dither cmd loop running"))
    while GlobalVars.forceTerminate == 0:
        
        sleep(1)
        text = "doDither value = : " + str(GlobalVars.doPhdDither)
        setMessage(buildMessage("DEBUG",text))
        if GlobalVars.doPhdDither == 1:
            #setMessage("STATUS: Dither command rcvd \r\n")
            setMessage(buildMessage("STATUS", "Dither command rcvd"))
            #found two "larger" dither commands
            ditherAmount = 5
            ditherCmd = GlobalVars.cmd_list["DD"]
            if ditherCmd < 4:
                ditherAmount = ditherCmd + 2
            else:
                ditherAmount = ditherCmd + 8
            msg = chr(ditherAmount)
            phd_cmd_socket.send(msg.encode())
            GlobalVars.doPhdDither = 0
    setMessage(buildMessage("DEBUG", "exit dither cmd loop"))
#============================================================================
#============================================================================


def setMessage(inmessage):


    lock.acquire()
    try:
        GlobalVars.message.append(inmessage)
    except:
        print "write message error"
    finally:
        lock.release()

def readMessage():


    themessage = []
    lock.acquire()
    try:
        themessage = GlobalVars.message
        GlobalVars.message = []
    except:
        print "read message error"
    finally:
        lock.release()

    return themessage


def doparseLine(line):

    res = line.split(":")
    if len(res) != 2:
        #setMessage("STATUS: invalid config line")
        setMessage(buildMessage("WARNING", "invalid config line"))
        return
    if res[0] in GlobalVars.valid_commands:
        if res[0] == "PA":
            GlobalVars.cmd_list[res[0]] = res[1]
        else:
            GlobalVars.cmd_list[res[0]] = int(res[1])
        #setMessage("STATUS: Config Line: " + line)
        setMessage(buildMessage("INFO","Config line " + line))

#/////////////////////////////////////
def runLoop():

    while 1:

        sleep(4)
        #setMessage("DEBUG: run loop \r\n")
        setMessage(buildMessage("STATUS", "Run loop"))
        if GlobalVars.startCaptureClicked == 1:

            if GlobalVars.CaptureThreadRunning == 0 and GlobalVars.PHDThreadRunning == 0:
                #setMessage("STATUS: in run loop \r\n")
                setMessage(buildMessage("DEBUG", "in run loop"))
                GlobalVars.is_guiding = 0
                GlobalVars.terminate = 0
                GlobalVars.forceTerminate = 0
                GlobalVars.isDithering = 0
                t2 = 0

                t1 = threading.Thread(target=threaded_listen, args=[])
                if GlobalVars.cmd_list["LS"] == 0:
                    t2 = threading.Thread(target=threaded_send, args=[])
                else:
                    t2 = threading.Thread(target=threaded_livestack, args=[])
                t3 = threading.Thread(target=phdDither, args=[])
                t1.start()
                t2.start()
                t3.start()
                GlobalVars.startCaptureClicked = 0

        if GlobalVars.stopCaptureClicked == 1 or GlobalVars.terminate == 1:
            GlobalVars.forceTerminate = 1
            #setMessage("STATUS: Run Complete \r\n")
            setMessage(buildMessage("STATUS","Run complete"))
            GlobalVars.stopCaptureClicked = 0
#            t1.join()
#            t2.join()
#            t3.join()

    setMessage(buildMessage("STATUS"," run loop exit "))

def statusLoop():

    message = []
    lastmessage = ""
    isConnectedToStatusMonitor = 1
    endStatusLoop = 0
    s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s2.connect((statushost, shport))
    except:
        print 'Unable to connect to status monitor'
        isConnectedToStatusMonitor = 0
    #    exit()
    if not USE_SHARP_CAP:
        startCapture()

    if isConnectedToStatusMonitor == 1:
        s2.sendall(b"STATUS: Running \r\n")

    while endStatusLoop == 0:
        sleep(0.5)
        message = readMessage()

        if len(message) > 0:
            if isConnectedToStatusMonitor == 1:
                s2.sendall(message.encode())
            else:
                for m in message:
                    msg = m["msg"]
                    level = m["type"]
                    if msg != lastmessage:
                        print msg
                        lastmessage = msg
                    if m == "endstatusloop":
                        endStatusLoop = 1
                    message = []

    print "exit status loop"
    s2.close()



def startCapture():

    GlobalVars.forceTerminate = 0
    GlobalVars.terminate = 0
    GlobalVars.stopCaptureClicked = 0
    #setMessage("EVENT: Start clicked \r\n")
    print "start clicked"
    setMessage(buildMessage("INFO", "Start clicked"))
    filepath = GlobalVars.cmd_list["CF"]
    if os.path.isfile(filepath):
        with open(filepath) as fp:
            for line in fp:
                doparseLine(line)
    GlobalVars.startCaptureClicked = 1


def stopCapture():

    GlobalVars.stopCaptureClicked = 1

if USE_SHARP_CAP:
    SharpCap.AddCustomButton("Start", None, "StartDitheredRun", startCapture)
    SharpCap.AddCustomButton("Stop", None, "StopDitheredRun", stopCapture)

t3 = threading.Thread(target=runLoop, args=[])
t4 = threading.Thread(target=statusLoop, args=[])
t3.start()
t4.start()


print "done"
