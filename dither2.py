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
import urllib2

#===========================================================================
#==========================================================================
#defualts for new dither call
#
GlobalVars.cmd_list["DP"] = 10  #dither up to this many pixels
GlobalVars.cmd_list["RA"] = 1   #dither in ra only 1 = true 0 = False
GlobalVars.cmd_list["SR"] = 1.5 #how close to locked star to be SettleDone
GlobalVars.cmd_list["SD"] = 5   #how long must you be that close
GlobalVars.cmd_list["SM"] = 40  #time out value
#'{"method": "dither", "params": [10, false, {"pixels": 1.5, "time": 8, "timeout": 40}], "id": 42}\r\n'

def buildDitherString():
    message = '{"method": "dither", "params": ['
    message = message + str(GlobalVars.cmd_list["DP"])
    if(GlobalVars.cmd_list["RA"] == 1):
        message = message + ', true, { "pixels": '
    else:
        message = message + ', false,  { "pixels": '

    message = message + str(GlobalVars.cmd_list["SR"])
    message = message + ', "time": '
    message = message + str(GlobalVars.cmd_list["SD"])
    message = message + ', "timeout": '
    message = message + str(GlobalVars.cmd_list["SM"])
    message = message + '}], "id":' + str(42) + '}\r\n'
    GlobalVars.ditherstring = message
    setMessage(buildMessage("DEBUG", GlobalVars.ditherstring))

#===========================================================================
#==========================================================================
# globals .. doesnt make me happy but it works :)
#for Testing without sharpcap use 0

USE_SHARP_CAP = 1
host = '127.0.0.1'
port = 4400

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
        if GlobalVars.localImageCounter > 5:
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
#============================================================================
#===========================================================================

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

#==========================================================================
#=========================================================================+
# this function is the thread that deals with SharpCap standard capture
def dither_while_captureing():

    GlobalVars.CaptureThreadRunning = 1
    totalCount = 0
    ditherCount = 0
    GlobalVars.terminate = 0
    setMessage(buildMessage("STATUS", "Sharp cap standard thread"))




#==========================================================================
#=========================================================================
def runLoop()
    while 1:
    
        sleep(5)


