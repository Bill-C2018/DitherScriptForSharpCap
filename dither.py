#<head></head>
#<body>
#<h2><center>This software is copyright 2018<br>
#Bill Cunning / CSoft Software
#</center>
#</h2>
#<h3>
#This software is licensed under the Creative Commons License and may be modified and shared as long as the terms of the license are followed
#</h3>
#<a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by-nc-sa/4.0/88x31.png" /></a><br />This work is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/">Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License</a>.
#</body>
#
#A big thank you to DonBoy from CloudyNights forums for all the testing and suggestions he has and continues to make!
#

import datetime, socket, sys, json, threading
import os
from time import sleep

#=============================================================================================
#
CmdList = {}
#=============================================================================================
#	edit these values
#=============================================================================================
#these need to be set for your specific setup
#total frames to take
CmdList["FC"] = 13
#dither ever DE frames
CmdList["DE"] = 5
#path to actual dither program
#Dither command line
CmdList["PA"] = 'c:/phddither/phd_dither.exe 1 true'
#path to config file
CmdList["CF"] = 'C:/Users/bill/Documents/sharpcapscripts/config.txt'
#stop when guiding stops .. if set to one .. otherwise will run till frameCount
#is reached or the stop button is pushed
CmdList["GS"] = 1
#if set to 0 use the phddither.exe application if set to 1, 2, or 3
#dither with phd directly at that level of dithereing (low medium high) 
CmdList["DD"] = 2
#set to one if you are doing live stacking 
#0 otherwise
CmdList["LS"] = 1
#wait one frame after we recieve settledone if set to one else
#start stacking as soon as we get the settle done
CmdList["SD"] = 1
#================================================================================================
#================================================================================================
#=========== from here downward is optional - if left as is it will use the 
#=========== current SharpCap settings
#================================================================================================
#if Use Current Settings (UC) is set to one it will use the current sharp cap settings
#if set to 0 will use the following values to reset the sharpcap settings and then use those
CmdList["UC"] = 1
#if UC is 0 and UF is one read the file config.txt for these values
CmdList["UF"] = 0
#if UC = 0 and UF = 0 use these default values
#exposure
CmdList["EX"] = 0.1
#gain
CmdList["GA"] = 50
#ColorSpace
CmdList["CS"] = "RAW16"
#output format
CmdList["OF"] = "FITS files (*.fits)"

#======================================================================================
#======================================================================================
# globals .. doesnt make me happy but it works :) 

#for Testing without sharpcap use 0
useSharpCap = 1

host = '127.0.0.1'
port = 4400
ditherport = 4300

isGuiding = 0
terminate = 0
forceTerminate = 0
isDithering = 0
PHDThreadRunning = 0
CaptureThreadRunning = 0
startCaptureClicked = 0
stopCaptureClicked = 0
phdConnected = 0
message = []
doPhdDither = 0
needsunpausing = 0

lock = threading.Lock()

validCommands = ["FC","DE","PA","GS","EX","GA","DD", "LS", "SD"]


#======================================================================================
#======================================================================================
# stub out the calls to sharp cap
localImageCounter = 0;
fakedImages = 0;

def sharpCapInitCapture( useSharpCap ) :
	global localImageCounter
	global fakedImages

	localImageCounter = 0
	fakedImages = 0
	if useSharpCap :
		try:
			# _______setup capture Blue (limited , count, wait)
			SharpCap.SelectedCamera.CaptureConfig.CaptureLimitType = SharpCap.SelectedCamera.CaptureConfig.CaptureLimitType.FrameLimited
			#____________  make sharp cap think its a couple longer than we want . if they both shut down at the same time
			#____________  we get into a race condition
			SharpCap.SelectedCamera.CaptureConfig.CaptureLimitValue = CmdList["FC"] + 2
			SharpCap.SelectedCamera.CaptureConfig.CaptureSequenceCount = 1
			SharpCap.SelectedCamera.CaptureConfig.CaptureSequenceInterval = 0	
		except:
		#this is fatal abort 
			print("fatal error - restart sharpcap and select camera first")
			sys.exit();
			
def sharpCapIsCapturing( useSharpCap ) :
	
	if useSharpCap :
		return SharpCap.SelectedCamera.Capturing
	else :
		return True
		
def sharpCapGetImageCount( useSharpCap ) :
	global localImageCounter
	global fakedImages
	
	if useSharpCap :
		return SharpCap.SelectedCamera.CapturedFrameCount
	else :
		localImageCounter = localImageCounter + 1
		if localImageCounter > 10:
			fakedImages = fakedImages + 1
			localImageCounter = 0
	return fakedImages
	
def sharpCapToggleCameraPaused( useSharpCap, value ) :
	
	if useSharpCap :
		SharpCap.SelectedCamera.Paused = value
		
	
			
def sharpCapPrepareAndRun( useSharpCap ) :
	global needsunpausing
	
	if useSharpCap :
		if not SharpCap.SelectedCamera.Capturing :
			setMessage("STATUS: preparing capture \r\n")
			SharpCap.SelectedCamera.PrepareToCapture()
			SharpCap.SelectedCamera.RunCapture()
		else :
			if needsunpausing == 1 :
				setMessage("STATUS: resuming \r\n")
				SharpCap.SelectedCamera.Paused = False
				needsunpausing = 0
	else :
		if needsunpausing == 1 :
			setMessage("STATUS: resuming \r\n")
			needsunpausing = 0
			
			
def sharpCapStopCapture( useSharpCap ) :
	if useSharpCap :
		if SharpCap.SelectedCamera.Capturing :
			SharpCap.SelectedCamera.StopCapture()
		
#======================================================================================
#======================================================================================
#this is the sharp cap thread if live stacking 
def threaded_livestack() :
	global terminate
	global isGuiding
	global CmdList
	global isDithering
	global forceTerminate
	global CaptureThreadRunning
	global doPhdDither
	global messagecount
	global useSharpCap
	global needsunpausing
	
	CaptureThreadRunning = 1
	
	lastTotalCount = 0
	totalCount = 0
	ditherCount = 0
	terminate = 0
	waitoneframe = 0
	
	lastTotalCount = SharpCap.SelectedCamera.CapturedFrameCount
	
	setMessage("STATUS: live capture runninig \r\n")
	while forceTerminate == 0 :
		sleep(2)
		
		
		#setMessage("STATUS: live capture loop1 \r\n")
		totalCount = SharpCap.SelectedCamera.CapturedFrameCount			
		#setMessage("STATUS: live capture loop2 \r\n")	
		
		if isDithering == 1 and needsunpausing == 1:
			waitoneframe = totalCount
			lastTotalCount = totalCount
		else:
			if needsunpausing == 0 :
				ditherCount = totalCount - lastTotalCount
		
		setMessage("STATUS: dither count " + str(ditherCount) + " \r\n")
		if isDithering == 0 and needsunpausing == 1:
			if CmdList["SD"] == 1 :
				if totalCount > waitoneframe :
					SharpCap.LiveStacking.Parameters.Paused = False
					needsunpausing = 0;
					lastTotalCount = totalCount
			else :
				SharpCap.LiveStacking.Parameters.Paused = False
				needsunpausing = 0;
				lastTotalCount = totalCount
			
			
		if ditherCount >= CmdList["DE"]	:
			setMessage("STATUS: dither start \r\n")
			SharpCap.LiveStacking.Parameters.Paused = True
			lastTotalCount = totalCount
					
			ditherCount = 0
			isDithering = 1
			if CmdList["DD"] == 0 :
				os.system(CmdList["PA"]) 
			else :
				setMessage("STATUS: Sending dither command \r\n")
				doPhdDither = 1
						
			needsunpausing = 1
					
	CaptureThreadRunning = 0
	setMessage("STATUS: end live capture thread \r\n")
	
#======================================================================================
#======================================================================================
# this function is the thread that deals with SharpCap
def threaded_send() :
	global terminate
	global isGuiding
	global CmdList
	global isDithering
	global forceTerminate
	global CaptureThreadRunning
	global doPhdDither
	global messagecount
	global useSharpCap
	lastTotalCount = 0
	global needsunpausing
	
	sharpCapInitCapture(useSharpCap)
	CaptureThreadRunning = 1;
	
	totalCount = 0
	ditherCount = 0
	terminate = 0

	while terminate == 0:
		sleep(2)
		if CmdList["GS"] == 1 :
			doCapture = isGuiding
		else:
			doCapture = 1
		if isDithering == 0 and doCapture == 0 :
			setMessage( "STATUS: Waiting \r\n")
		if isDithering == 1 :
			setMessage( "STATUS: Dithering \r\n")
		if isDithering == 0 and doCapture == 1 :
			setMessage("STATUS: Capturing \r\n")
		
		if isDithering == 0 :
			if doCapture == 1 :
				
				if sharpCapIsCapturing( useSharpCap ) :
					totalCount = sharpCapGetImageCount( useSharpCap )
				else :
					totalCount = 0
					
				setMessage("STATUS: Total Count = " + str(totalCount))
				ditherCount = totalCount - lastTotalCount
				sharpCapPrepareAndRun( useSharpCap )
				
						
				if ditherCount >= CmdList["DE"]	:
					setMessage("STATUS: dither start \r\n")
					lastTotalCount = totalCount
					sharpCapToggleCameraPaused( useSharpCap, True)
					
					ditherCount = 0
					isDithering = 1
					if CmdList["DD"] == 0 :
						os.system(CmdList["PA"]) 
					else :
						setMessage("STATUS: Sending dither command \r\n")
						doPhdDither = 1
						
					needsunpausing = 1
					
		if totalCount >= CmdList["FC"] :
			setMessage("STATUS: exit capture thread on count \r\n")
			CaptureThreadRunning = 0
			sharpCapStopCapture( useSharpCap )
			forceTerminate = 1
			terminate = 1
			exit()
		if forceTerminate == 1 :
			setMessage("STATUS: exit capture thread \r\n")
			#SharpCap.SelectedCamera.Paused = True
			CaptureThreadRunning = 0
			sharpCapStopCapture( useSharpCap )	
			exit()
		if terminate == 1 :
			setMessage("STATUS: exit capture thread \r\n")
			sharpCapStopCapture( useSharpCap )
			CaptureThreadRunning = 0
			exit()
#======================================================================================
#======================================================================================
#======================================================================================
#======================================================================================
# this function is the thread that listens for phd updates

def threaded_listen() :
	global isGuiding
	global forceTerminate
	global terminate
	global isDithering
	global CmdList
	global PHDThreadRunning
	PHDThreadRunning = 1
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	try :
		s.connect((host, port))
	except :
		print('Unable to connect to phd server')
		exit()

	for l in s.makefile() :
		m = json.loads(l)
		if 'Event' in m and m['Event'] != 'LoopingExposures' :
			setMessage("PHD: " + m['Event'] + "\r\n")
			if m['Event'] == 'StartGuiding' :
				isGuiding = 1
			if m['Event'] == 'GuideStep' :
				isGuiding = 1
			if m['Event'] == 'GuidingStopped' :
				isGuiding = 0
				if CmdList["GS"] == 1 :
					terminate = 1
			if m['Event'] == 'GuidingDithered' :
				isDithering = 1
			if m['Event'] == 'SettleDone' :
				isDithering = 0
		sleep(1)
		if forceTerminate == 1 :
			print("exit phd loop")
			PHDThreadRunning = 0
			exit()
		if terminate == 1 :
			print("phd loop exist")
			PHDThreadRunning = 0
			exit()
#======================================================================================
#======================================================================================
# this is the function / thread that sends the dither command to phd
def phdDither() :
	global terminate
	global doPhdDither
	global CmdList
	
	s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	try :
		s2.connect((host, ditherport))
	except :
		setMessage('STATUS: Unable to connect to phd server')
		exit()
	
	while terminate == 0 :
		sleep(1)
		if doPhdDither == 1 :
			setMessage("STATUS: Dither command rcvd \r\n")
			#found two "larger" dither commands
			ditherAmount = 5
			ditherCmd = CmdList["DD"]
			if ditherCmd < 4 :
				ditherAmount =  ditherCmd + 2
			else :
				ditherAmount = ditherCmd + 8
			msg = chr(ditherAmount)
			s2.send(msg.encode())
			doPhdDither = 0
#======================================================================================
#======================================================================================


def setMessage(inmessage) :
	global message
	global lock
	lock.acquire()
	try:
		message.append(inmessage)
	except :
		print("write message error")
	finally:
		lock.release()
		
def readMessage() :
	global message
	global lock
	themessage = []
	lock.acquire()
	try:
		themessage = message
		message = []
	except :
		print("read message error")
	finally:
		lock.release()
		
	return themessage
		

def doparseLine(line) :
	global CmdList
	global validCommands
	res = line.split(":")
	if len(res) != 2 :
		setMessage("STATUS: invalid config line")
		return
	if res[0] in validCommands :
		if(res[0] == "PA") :
			CmdList[res[0]] = res[1]
		else:
			CmdList[res[0]] = int(res[1])
		setMessage("STATUS: Config Line : " + line)
	
#/////////////////////////////////////
def runLoop() :
	global startCaptureClicked
	global stopCaptureClicked
	global CaptureThreadRunning
	global PHDThreadRunning
	global phdConnected
	global forceTerminate
	global terminate
	global isGuiding
	global isDithering
	global s
	
	while 1 :
		
		sleep(4)
		#setMessage("DEBUG: run loop \r\n")
		if startCaptureClicked == 1 :
		
			if CaptureThreadRunning == 0 and PHDThreadRunning == 0 :
				setMessage("STATUS: in run loop \r\n")
				isGuiding = 0
				terminate = 0
				forceTerminate = 0
				isDithering = 0
				t2 = 0
				
				t1 = threading.Thread(target=threaded_listen, args=[])
				if CmdList["LS"] == 0 :
					t2 = threading.Thread(target=threaded_send, args=[])
				else :
					t2 = threading.Thread(target=threaded_livestack, args=[])
				t3 = threading.Thread(target=phdDither, args=[])
				t1.start()
				t2.start()
				t3.start()
				startCaptureClicked = 0;
				
		if stopCaptureClicked == 1 or terminate == 1 :
			forceTerminate = 1
			setMessage("STATUS: Run Complete \r\n")
			stopCaptureClicked = 0
#			t1.join()
#			t2.join()
#			t3.join()
			
	setMessage("STATUS: run loop exit \r\n")
		
def statusLoop() :
	global messagecount
	message = []
	lastmessage = ""
	isConnectedToStatusMonitor = 1
	endStatusLoop = 0
	s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	try :
		s2.connect((statushost, shport))
	except :
		print('Unable to connect to status monitor')
		isConnectedToStatusMonitor = 0
	#	exit()
	if not useSharpCap :
		startCapture()
		
	if isConnectedToStatusMonitor == 1 :
		s2.sendall(b"STATUS: Running \r\n")
		
	while endStatusLoop == 0 :
		sleep(0.5)
		message = readMessage()
		#print("status loop")
		if len(message) > 0 :
			if isConnectedToStatusMonitor == 1 :
				s2.sendall(message.encode())
			else :
				for m in message :
					if m != lastmessage :
						print(m)
						lastmessage = m
					if m == "endstatusloop" :
						endStatusLoop = 1
					message = []

	print("exit status loop")		
	s2.close()		
	
	
	
def startCapture() :
	global startCaptureClicked
	global CmdList
	global forceTerminate
	global terminate
	global stopCaptureClicked

	
	forceTerminate = 0
	terminate = 0
	stopCaptureClicked = 0
	setMessage("EVENT: Start clicked \r\n")
	filepath = CmdList["CF"]
	if os.path.isfile(filepath):
		with open(filepath) as fp :
			for line in fp:
				doparseLine(line)
	startCaptureClicked = 1


def stopCapture() :
	global stopCaptureClicked
	stopCaptureClicked = 1

if useSharpCap :
	SharpCap.AddCustomButton("Start", None, "StartDitheredRun", startCapture)
	SharpCap.AddCustomButton("Stop", None, "StopDitheredRun", stopCapture)
	
t3 = threading.Thread(target=runLoop, args=[])
t4 = threading.Thread(target=statusLoop, args=[])
t3.start()
t4.start()


print("done")

	
