Dither for PHD2 and Sharpcap

Uses:  
	I use a standard Mead fork mounted scope on a wedge. I use the Mead provided software with SharpCap and Phd2 for almost all of my imaging. This left no way to dither automatically until recently when SharpCap introduced dithering while live stacking. I almost never use live stacking, and while I did try some of the work-arounds to simulate my normal long exposure captures, I wanted a more streamlined way of dithering while doing long exposure / long term sessions. 
	SimpleDither.py provides a loadable script that makes dithering fairly straight forward when using configurations the same as (or similar to) mine. You can edit the dither parameters before you load the script, or with python3 installed on your machine you can use the provided client.py to modify settings while the script is live. 

Configuration settings:
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


Dither Variables:

	RAOnly:  When set to True, PHD2 will only dither in the RA axis.
	MaxPixels: When PHD2 Dithers it uses a random number of pixels in the range of 1 to 			MaxPixels.

	SettleTarget: Guiding must be within this number of pixels for SettleDelay seconds before a 		“settle done” event is sent.
	SettleMaximum: The amount of time PHD will wait to “settle” in seconds. Once this limit is 		reached a “settledone” event will be sent regardless 
	DitherEvery:  Trigger a dither every DitherEvery captured frames.
	WaitForNextFrame:  If set to True will wait until the current frame that dithering occurred on is 		complete before enabling capture again.


CLIENT.PY

This is a simple command line app that allows you to update the dither variables in an already loaded and running simpledither.py script. 
***Requires python3 be installed on the machine you are running it from.

User adjustable settings:
	HOST_ADDRESS = "localhost"
	HOST_PORT = 5322

	Set the HOST_ADDRESS to the address of the machine sharpcap is running on. 
	(I run client.py on the same machine )
	
	HOST_PORT is the port the cmd listener is listening on in the simpledither 	program. Unless you change it in the simpledither script, leave it as is 	here.

	valid_cmds = ["ditherevery", "waitfornextframe", "raonly", "settletarget", 	"settledelay", "settlemax", "maxpixels", "ditherstring"]

	All but ditherstring can be set and retrieved, ditherstring only returns the         	current dither command that will be sent to PHD.


USAGE Examples:

	python3 client.py get dithervery  : will return the current setting for the ditherevery value
	python3 client.py set ditherevery 20 : will set the ditherevery value to 20 frames.
