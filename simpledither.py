
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


import socket
import sys
import json
import threading
import os
import time 
import urllib2
from time import sleep

#============================================================================
# these settings may be changed
#============================================================================

#this setting is in seconds, and should be less than the exposure time you have
#set in PHD
TIME_DELAY = 0.5

#These are the standard phd server settings assuming phd is running on the same
#machine as sharp cap
host = '127.0.0.1'
port = 4400

#These are the setting that control the actual phd dithering -- see readme for full
#explanation    
class DitherVariables:
    RAOnly = False
    MaxPixels = 10
    SettleTarget = 2
    SettleDelay = 10
    SettleMaximum = 60
    ditherEvery = 10
    waitForNextFrame = False

#///////////////////////////////////////////////////////////////////////
# nothing below here needs to be edited
#///////////////////////////////////////////////////////////////////////

class GlobalVariables:
    message = []
    doRun = True
    ditherstring = ""
    is_guiding = False
    is_dithering = False
    dither_started = False
    listenSocketConnected = False

cmd_port = 5322

#///////////////////////////////////////////////////////////////////////
#///////////////////////////////////////////////////////////////////////
#functions
#//////////////////////////////////////////////////////////////////////
#////////////////////////////////////////////////////////////////////////
def build_message(type,msg):
    message = {}
    message["type"] = type + ": "
    message["msg"] = msg
    return message

def set_message(inmessage):
    lock.acquire()
    try:
        GlobalVars.message.append(inmessage)
    except:
        print "write message error"
    finally:
        lock.release()

def read_message():
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
    
#///////////////////////////
def threaded_listen():

    if GlobalVars.listenSocketConnected == False:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((host, port))
        except:
            print 'Unable to connect to phd server'
            exit()
            
    GlobalVars.listenSocketConnected = True
            

    for l in s.makefile():
        m = json.loads(l)
        if 'Event' in m and m['Event'] != 'LoopingExposures':
            eventtext = m['Event']
            set_message(build_message("PHD", eventtext))
            if m['Event'] == 'StartGuiding':
                GlobalVars.is_guiding = True
            if m['Event'] == 'GuideStep' and GlobalVars.is_dithering != True:
                GlobalVars.is_guiding = True
            if m['Event'] == 'GuidingStopped':
                GlobalVars.is_guiding = False
            if m['Event'] == 'StarLost':
                GlobalVars.is_guiding = False                
            if m['Event'] == 'GuidingDithered':
                GlobalVars.is_guiding = False
            if m['Event'] == 'SettleBegin':
                GlobalVars.dither_started = True
            if m['Event'] == 'SettleDone':
                GlobalVars.is_guiding = True
            sleep(TIME_DELAY)


def wait_for_guiding():
    
    exposure = sharpCapGetExposureTime()
    message = "Exposure " + str(exposure)
    set_message(build_message("STATUS", message))
  
    while GlobalVars.dither_started == False:
        sleep(TIME_DELAY)

    GlobalVars.dither_started = False

 
    timenow = time.time()
    count = 0
    while GlobalVars.is_guiding == False:
        sleep(TIME_DELAY)

  
    if ditherVars.waitForNextFrame:
        texposure = exposure
        elapsed = time.time() - timenow
        while elapsed < (texposure + 10):
            sleep(TIME_DELAY)
            elapsed = time.time() - timenow
        
    
def phd_dither():
    message = GlobalVars.ditherstring
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((host, port))
    except:
        print 'Unable to connect to phd server'
        exit()
        
    s.sendall(message)
    s.close()

def build_dither_string():
    message = '{"method": "dither", "params": ['
    message = message + str(ditherVars.MaxPixels)
    if(ditherVars.RAOnly == True):
        message = message + ', true, { "pixels": '
    else:
        message = message + ', false,  { "pixels": '

    message = message + str(ditherVars.SettleTarget)
    message = message + ', "time": '
    message = message + str(ditherVars.SettleDelay)
    message = message + ', "timeout": '
    message = message + str(ditherVars.SettleMaximum)
    message = message + '}], "id":' + str(42) + '}\r\n'
    GlobalVars.ditherstring = message
    set_message(build_message("DEBUG", GlobalVars.ditherstring))
    
#///////////////////////////
def sharpCapGetImageCount():
    return SharpCap.SelectedCamera.CapturedFrameCount
    
def sharpCapIsCapturing():
    return SharpCap.SelectedCamera.Capturing
    
def sharpCapGetExposureTime():
    return SharpCap.SelectedCamera.Controls.Exposure.Value
    
#//////////////////////////////

def do_dither():
    if GlobalVars.is_guiding == True: 
        SharpCap.SelectedCamera.Paused = True
        set_message(build_message("STATUS", "Dithering"))
        set_message(build_message("STATUS", GlobalVars.ditherstring ))
        GlobalVars.is_dithering = True
        GlobalVars.is_guiding = False
        phd_dither()
        GlobalVars.is_guiding = False
        wait_for_guiding()
        GlobalVars.is_dithering = False
        SharpCap.SelectedCamera.Paused = False

#//////////////////////////////
def status_loop():

#no status server for now
    statusListener = False

    message = GlobalVars.ditherstring
        
    lastmessage = ""
    while GlobalVars.doRun == True:
        sleep(TIME_DELAY)
        message = read_message()
        if len(message) > 0 :
            if statusListener == False:
                for m in message:
                    msg = m["msg"]
                    level = m["type"]                
                    if 1:
                        print msg
                        lastmessage = msg
            else:
                s.send(message)

#///////////////////////////
#///////////////////////////////////////////////////////////////
#server code for getting and setting values
def build_response(status,value):
            
    message = "status : " + status + " value : " + value 
    return message 
    
def endofLine():

    return "\r\n"
    
def send_response(connection,msg,closeConnection):

    connection.sendall(bytes(msg,'ascii'))
    connection.sendall(bytes(endofLine(),'ascii'))
    if closeConnection:
        connection.close()

def cmd_listener():

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = (host, cmd_port)
    
    sock.bind(server_address)
    sock.listen(1)
    
    #This should always run
    #while GlobalVars.doRun == True:
    while True:
    
        print("waiting for connection")
        connection, client_address = sock.accept()
        print("connected")
        try:
            #while GlobalVars.doRun == True:
            while True:    
                data = connection.recv(100)
                sdata = str(data,'ascii')
                obj = json.loads(sdata)
                CMD = (obj["cmd"])
                OP = (obj["op"])
                VALUE = (obj["value"])
                if OP == "set" :
                    print("SET")
                    if CMD == "waitfornextframe" :
                        if VALUE == "false" :
                            ditherVars.waitForNextFrame = False
                            message = build_response("SET : OK",str(ditherVars.waitForNextFrame))
                            send_response(connection,message,True)
                            break    
                        else:
                            ditherVars.waitForNextFrame = True
                            message = build_response("SET : OK",str(ditherVars.waitForNextFrame))
                            send_response(connection,message,True)
                            break    
                    elif CMD == "raonly":
                        if VALUE == "false" :
                            ditherVars.RAOnly = False
                            message = build_response("SET : OK",str(ditherVars.RAOnly))
                            send_response(connection,message,True)
                            break    
                        else:
                            ditherVars.RAOnly = True
                            message = build_response("SET : OK",str(ditherVars.RAOnly))
                            send_response(connection,message,True)
                            break    
                    elif CMD == "ditherevery" :
                        number = int(VALUE)
                        if number > 0 :
                            ditherVars.ditherEvery = number
                            message = build_response("SET : OK",str(ditherVars.ditherEvery))
                            send_response(connection,message,True)
                            break
                        else:
                            message = build_response("SET : FAIL","Value must be greater than 0")
                            send_response(connection,message,True)
                            break
                    elif CMD == "settletarget" :
                        number = int(VALUE)
                        if number > 0 :
                            ditherVars.SettleTarget = number
                            message = build_response("SET : OK",str(ditherVars.SettleTarget))
                            send_response(connection,message,True)
                            break
                        else:
                            message = build_response("SET : FAIL","Value must be greater than 0")
                            send_response(connection,message,True)
                            break
                    elif CMD == "settledelay" :
                        number = int(VALUE)
                        if number > 0 :
                            ditherVars.SettleTarget = number
                            message = build_response("SET : OK",str(ditherVars.SettleDelay))
                            send_response(connection,message,True)
                            break
                        else:
                            message = build_response("SET : FAIL","Value must be greater than 0")
                            send_response(connection,message,True)
                            break
                    elif CMD == "settlemax" :
                        number = int(VALUE)
                        if number > 0 :
                            ditherVars.SettleMaximum = number
                            message = build_response("SET : OK",str(ditherVars.SettleMaximum))
                            send_response(connection,message,True)
                            break
                        else:
                            message = build_response("SET : FAIL","Value must be greater than 0")
                            send_response(connection,message,True)
                            break
                    elif CMD == "maxpixels" :
                        number = int(VALUE)
                        if number > 0 :
                            ditherVars.MaxPixels = number
                            message = build_response("SET : OK",str(ditherVars.MaxPixels))
                            send_response(connection,message,True)
                            break
                        else:
                            message = build_response("SET : FAIL","Value must be greater than 0")
                            send_response(connection,message,True)
                            break
                            
                            
                            
                elif OP == "get" :
                    print("GET")
                    if CMD == "waitfornextframe" :
                        message = build_response("GET : OK",str(ditherVars.waitForNextFrame))
                        send_response(connection,message,True)
                        break
                    elif CMD == "raonly" :
                        message = build_response("GET : OK",str(ditherVars.RAOnly))
                        send_response(connection,message,True)
                        break                        
                    elif CMD == "ditherevery" :
                        message = build_response("GET : OK",str(ditherVars.ditherEvery))
                        send_response(connection,message,True)
                        break                    
                    elif CMD == "settletarget" :
                        message = build_response("GET : OK",str(ditherVars.SettleTarget))
                        send_response(connection,message,True)
                        break
                    elif CMD == "settledelay" :
                        message = build_response("GET : OK",str(ditherVars.SettleDelay))
                        send_response(connection,message,True)
                        break
                    elif CMD == "settlemax" :
                        message = build_response("GET : OK",str(ditherVars.SettleMaximum))
                        send_response(connection,message,True)
                        break
                    elif CMD == "maxpixels" :
                        message = build_response("GET : OK",str(ditherVars.MaxPixels))
                        send_response(connection,message,True)
                        break    
                    elif CMD == "ditherstring" :
                        build_dither_string()
                        message = build_response("GET : OK",str(GlobalVars.ditherstring))
                        send_response(connection,message,True)
                        break                        


        except:
            # Clean up the connection
            print("in exception")
            connection.sendall(bytes(endofLine(),'ascii'))
            connection.close()    
            sock.close()
            sys.exit()
            
    sock.close()
                            
#///////////////////////////////////////
def main_run_loop():

    localFrameCount = 0
    lastHardFrameCount = 0
    build_dither_string()
    while GlobalVars.doRun == True:
        sleep(TIME_DELAY)
        if GlobalVars.is_guiding == True:
            if SharpCap.SelectedCamera.Paused == True:
                SharpCap.SelectedCamera.Paused = False
        else:
            if SharpCap.SelectedCamera.Paused == False:
                SharpCap.SelectedCamera.Paused = True
                
                
        if sharpCapIsCapturing():
            set_message(build_message("STATUS", "capturing"))
            frameCount = sharpCapGetImageCount()
            message = "Frame count " + str(frameCount)
            set_message(build_message("STATUS", message))
            if lastHardFrameCount != frameCount:
                lastHardFrameCount = frameCount
                localFrameCount = localFrameCount + 1
                if localFrameCount >= ditherVars.ditherEvery:
                    do_dither()
                    localFrameCount = 0
        else:
            set_message(build_message("STATUS", "looping"))
            localFrameCount = lastHardFrameCount = 0
        

def stop_script():
    GlobalVars.doRun = False
    
def start_script():
    GlobalVars.doRun = True
    tRun = threading.Thread(target=main_run_loop, args=[])
    tStatus = threading.Thread(target=status_loop, args=[])
    tPhd = threading.Thread(target=threaded_listen, args=[])
    tRun.start()
    tStatus.start()
    tPhd.start()    
    


#///////////////////////////////////////////////////////////////////////
#///////////////////////////////////////////////////////////////////////
#main
#//////////////////////////////////////////////////////////////////////
#////////////////////////////////////////////////////////////////////////
GlobalVars = GlobalVariables
ditherVars = DitherVariables
lock = threading.Lock()

SharpCap.AddCustomButton("Start", None, "StartDitheredRun", start_script)
SharpCap.AddCustomButton("Stop", None, "StopDitheredRun", stop_script)

command_thread = threading.Thread(target=cmd_listener, args=[])
command_thread.start()
