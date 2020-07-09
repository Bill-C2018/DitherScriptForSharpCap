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
def sharpCapGetImageCount():
	return SharpCap.SelectedCamera.CapturedFrameCount
	
def sharpCapIsCapturing():
	return SharpCap.SelectedCamera.Capturing
	
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

	while GlobalVars.doRun == True:
		sleep(1)
		if sharpCapIsCapturing():
			setMessage(buildMessage("STATUS", "capturing"))
			frameCount = sharpCapGetImageCount()
			message = "Frame count " + str(frameCount)
			setMessage(buildMessage("STATUS", message))
		else:
			setMessage(buildMessage("STATUS", "looping"))
		

#///////////////////////////////////////////////////////////////////////
#///////////////////////////////////////////////////////////////////////
#main
#//////////////////////////////////////////////////////////////////////
#////////////////////////////////////////////////////////////////////////
GlobalVars = GlobalVariables
lock = threading.Lock()

tRun = threading.Thread(target=mainRunLoop, args=[])
tStatus = threading.Thread(target=statusLoop, args=[])
tRun.start()
tStatus.start()