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
	dither_started = False
	waitForNextFrame = False
	listenSocketConnected = False
	
class DitherVariables:
	RAOnly = False
	MaxPixels = 10
	SettleTarget = 2
	SettleDelay = 10
	SettleMaximum = 60

host = '127.0.0.1'
port = 4400

cmd_port = 5322

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
			setMessage(buildMessage("PHD", eventtext))
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
			sleep(1)


def waitForGuiding():
	exposure = sharpCapGetExposureTime()
	message = "Exposure " + str(exposure)
	setMessage(buildMessage("STATUS", message))
	
	while GlobalVars.dither_started == False:
		sleep(1)

# we have seen the settle begin event which set it to true
# so we can set it back to false		
	GlobalVars.dither_started = False
	
	timenow = time.time()
	count = 0
	while GlobalVars.is_guiding == False:
		sleep(1)
		count = count + 1
		setMessage(buildMessage("STATS", str(count)))
		if count > int(ditherVars.SettleMaximum) :
			setMessage(buildMessage("STATUS","setting is guiding to true"))
			GlobalVars.is_guiding = True

	
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
		
	s.sendall(message)
	s.close()

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
	if GlobalVars.is_guiding == True: 
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
#///////////////////////////////////////////////////////////////
#server code for getting and setting values
def buildResponse(status,value):
			
	message = "status : " + status + " value : " + value 
	return message 
	
def endofLine():

	return "\r\n"
	
def sendResponse(connection,msg,closeConnection):

	connection.sendall(bytes(msg,'ascii'))
	connection.sendall(bytes(endofLine(),'ascii'))
	if closeConnection:
		connection.close()

def cmdListener():

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
							GlobalVars.waitForNextFrame = False
							message = buildResponse("SET : OK",str(GlobalVars.waitForNextFrame))
							sendResponse(connection,message,True)
							break	
						else:
							GlobalVars.waitForNextFrame = True
							message = buildResponse("SET : OK",str(GlobalVars.waitForNextFrame))
							sendResponse(connection,message,True)
							break	
					elif CMD == "raonly":
						if VALUE == "false" :
							ditherVars.RAOnly = False
							message = buildResponse("SET : OK",str(ditherVars.RAOnly))
							sendResponse(connection,message,True)
							break	
						else:
							ditherVars.RAOnly = True
							message = buildResponse("SET : OK",str(ditherVars.RAOnly))
							sendResponse(connection,message,True)
							break	
					elif CMD == "ditherevery" :
						number = int(VALUE)
						if number > 0 :
							GlobalVars.ditherEvery = number
							message = buildResponse("SET : OK",str(GlobalVars.ditherEvery))
							sendResponse(connection,message,True)
							break
						else:
							message = buildResponse("SET : FAIL","Value must be greater than 0")
							sendResponse(connection,message,True)
							break
					elif CMD == "settletarget" :
						number = int(VALUE)
						if number > 0 :
							ditherVars.SettleTarget = number
							message = buildResponse("SET : OK",str(ditherVars.SettleTarget))
							sendResponse(connection,message,True)
							break
						else:
							message = buildResponse("SET : FAIL","Value must be greater than 0")
							sendResponse(connection,message,True)
							break
					elif CMD == "settledelay" :
						number = int(VALUE)
						if number > 0 :
							ditherVars.SettleTarget = number
							message = buildResponse("SET : OK",str(ditherVars.SettleDelay))
							sendResponse(connection,message,True)
							break
						else:
							message = buildResponse("SET : FAIL","Value must be greater than 0")
							sendResponse(connection,message,True)
							break
					elif CMD == "settlemax" :
						number = int(VALUE)
						if number > 0 :
							ditherVars.SettleMaximum = number
							message = buildResponse("SET : OK",str(ditherVars.SettleMaximum))
							sendResponse(connection,message,True)
							break
						else:
							message = buildResponse("SET : FAIL","Value must be greater than 0")
							sendResponse(connection,message,True)
							break
					elif CMD == "maxpixels" :
						number = int(VALUE)
						if number > 0 :
							ditherVars.MaxPixels = number
							message = buildResponse("SET : OK",str(ditherVars.MaxPixels))
							sendResponse(connection,message,True)
							break
						else:
							message = buildResponse("SET : FAIL","Value must be greater than 0")
							sendResponse(connection,message,True)
							break
							
							
							
				elif OP == "get" :
					print("GET")
					if CMD == "waitfornextframe" :
						message = buildResponse("GET : OK",str(GlobalVars.waitForNextFrame))
						sendResponse(connection,message,True)
						break
					elif CMD == "raonly" :
						message = buildResponse("GET : OK",str(ditherVars.RAOnly))
						sendResponse(connection,message,True)
						break						
					elif CMD == "ditherevery" :
						message = buildResponse("GET : OK",str(GlobalVars.ditherEvery))
						sendResponse(connection,message,True)
						break					
					elif CMD == "settletarget" :
						message = buildResponse("GET : OK",str(ditherVars.SettleTarget))
						sendResponse(connection,message,True)
						break
					elif CMD == "settledelay" :
						message = buildResponse("GET : OK",str(ditherVars.SettleDelay))
						sendResponse(connection,message,True)
						break
					elif CMD == "settlemax" :
						message = buildResponse("GET : OK",str(ditherVars.SettleMaximum))
						sendResponse(connection,message,True)
						break
					elif CMD == "maxpixels" :
						message = buildResponse("GET : OK",str(ditherVars.MaxPixels))
						sendResponse(connection,message,True)
						break	
					elif CMD == "ditherstring" :
						buildDitherString()
						message = buildResponse("GET : OK",str(GlobalVars.ditherstring))
						sendResponse(connection,message,True)
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
def mainRunLoop():

	localFrameCount = 0
	lastHardFrameCount = 0
	buildDitherString()
	while GlobalVars.doRun == True:
		sleep(1)
		if GlobalVars.is_guiding == True:
			if SharpCap.SelectedCamera.Paused == False:
				SharpCap.SelectedCamera.Paused = True
		else:
			if SharpCap.SelectedCamera.Paused == True:
				SharpCap.SelectedCamera.Paused = False
				
				
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

command_thread = threading.Thread(target=cmdListener, args=[])
command_thread.start()

