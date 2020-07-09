import socket
import sys
import json
import threading
import os
from time import sleep
import urllib2

class GlobalVariables:
	message = []
	doRun = True
	ditherEvery = 5
	ditherstring = ""
	is_guiding = False
	is_dithering = False;
	
class DitherVariables:
	RAOnly = False
	MaxPixels = 10
	SettleTarget = 2
	SettleDelay = 10
	SettleMaximum = 60

host = '127.0.0.1'
port = 4400

#///////////////////////////////////////////////////////////////////////
#///////////////////////////////////////////////////////////////////////
#functions
#//////////////////////////////////////////////////////////////////////
#////////////////////////////////////////////////////////////////////////
def buildMessage(type,msg):
	message = {}
	message["type"] = type + ": "
	message["msg"] = msg
	return message

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
	
#///////////////////////////
def threaded_listen():

	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	try:
		s.connect((host, port))
	except:
		print 'Unable to connect to phd server'
		exit()

	for l in s.makefile():
		m = json.loads(l)
		if 'Event' in m and m['Event'] != 'LoopingExposures':
			eventtext = m['Event']
			setMessage(buildMessage("PHD", eventtext))
			if m['Event'] == 'StartGuiding':
				GlobalVars.is_guiding = True
			if m['Event'] == 'GuideStep' and GlobalVars.is_dithering != True:
				GlobalVars.is_guiding = True
			if m['Event'] == 'GuidingStopped':
				GlobalVars.is_guiding = False
			if m['Event'] == 'GuidingDithered':
				GlobalVars.is_guiding = False
			if m['Event'] == 'SettleDone':
				GlobalVars.is_guiding = True
			sleep(1)
			if GlobalVars.doRun == False:
				exit()

def waitForGuiding():
	while GlobalVars.is_guiding == False:
		sleep(1)
		

def phdDither():
	message = GlobalVars.ditherstring
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	try:
		s.connect((host, port))
	except:
		print 'Unable to connect to phd server'
		exit()
		
	s.send(message)

def buildDitherString():
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
	setMessage(buildMessage("DEBUG", GlobalVars.ditherstring))
	
#///////////////////////////
def sharpCapGetImageCount():
	return SharpCap.SelectedCamera.CapturedFrameCount
	
def sharpCapIsCapturing():
	return SharpCap.SelectedCamera.Capturing
	
#//////////////////////////////

def doDither():
	SharpCap.SelectedCamera.Paused = True
	setMessage(buildMessage("STATUS", "Dithering"))
	setMessage(buildMessage("STATUS", GlobalVars.ditherstring ))
	GlobalVars.is_dithering = True
	GlobalVars.is_guiding = False
	phdDither()
	GlobalVars.is_guiding = False
	waitForGuiding()
	GlobalVars.is_dithering = False
	SharpCap.SelectedCamera.Paused = False

#//////////////////////////////
def statusLoop():

	lastmessage = ""
	while GlobalVars.doRun == True:
		sleep(1)
		message = readMessage()
		if len(message) > 0 :
			for m in message:
				msg = m["msg"]
				level = m["type"]				
				if 1:
					print msg
					lastmessage = msg

#///////////////////////////
def mainRunLoop():

	localFrameCount = 0
	lastHardFrameCount = 0
	buildDitherString()
	while GlobalVars.doRun == True:
		sleep(1)
		if sharpCapIsCapturing():
			setMessage(buildMessage("STATUS", "capturing"))
			frameCount = sharpCapGetImageCount()
			message = "Frame count " + str(frameCount)
			setMessage(buildMessage("STATUS", message))
			if lastHardFrameCount != frameCount:
				lastHardFrameCount = frameCount
				localFrameCount = localFrameCount + 1
				if localFrameCount >= GlobalVars.ditherEvery:
					doDither()
					localFrameCount = 0
		else:
			setMessage(buildMessage("STATUS", "looping"))
			localFrameCount = lastHardFrameCount = 0
		

def stopScript():
	GlobalVars.doRun = False
	

#///////////////////////////////////////////////////////////////////////
#///////////////////////////////////////////////////////////////////////
#main
#//////////////////////////////////////////////////////////////////////
#////////////////////////////////////////////////////////////////////////
GlobalVars = GlobalVariables
ditherVars = DitherVariables
lock = threading.Lock()


SharpCap.AddCustomButton("Stop", None, "StopDitheredRun", stopScript)
tRun = threading.Thread(target=mainRunLoop, args=[])
tStatus = threading.Thread(target=statusLoop, args=[])
tPhd = threading.Thread(target=threaded_listen, args=[])
tRun.start()
tStatus.start()
tPhd.start()