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

class GlobalVariables:
	message = []
	doRun = True
	ditherEvery = 10
	ditherstring = ""
	is_guiding = False
	is_dithering = False
	waitForNextFrame = True
	
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
	exposure = sharpCapGetExposureTime()
	message = "Exposure " + str(exposure)
	setMessage(buildMessage("STATUS", message))
	timenow = time.time()
	while GlobalVars.is_guiding == False:
		sleep(1)
	
	if GlobalVars.waitForNextFrame:
		texposure = exposure
		elapsed = time.time() - timenow
		while elapsed < (texposure + 10):
			sleep(1)
			elapsed = time.time() - timenow
		
	
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
	
def sharpCapGetExposureTime():
	return SharpCap.SelectedCamera.Controls.Exposure.Value
	
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

#no status server for now
	statusListener = False

	message = GlobalVars.ditherstring
		
	lastmessage = ""
	while GlobalVars.doRun == True:
		sleep(1)
		message = readMessage()
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
	
def startScript():
	GlobalVars.doRun = True
	tRun = threading.Thread(target=mainRunLoop, args=[])
	tStatus = threading.Thread(target=statusLoop, args=[])
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

SharpCap.AddCustomButton("Start", None, "StartDitheredRun", startScript)
SharpCap.AddCustomButton("Stop", None, "StopDitheredRun", stopScript)
