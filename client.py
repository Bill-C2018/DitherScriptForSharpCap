import socket
import sys
import json


endOfLine = "\r\n"
valid_cmds = ["ditherevery","waitfornextframe","raonly", "settletarget", "settledelay"]
valid_ops = ["get", "set"]

def isValidCmd(cmd):

	for x in valid_cmds:
		if x == cmd:
			return True
		
	return False

def isValidOp(op):	

	for x in valid_ops:
		if x == op:
			return True
		
	return False
	
print(str(sys.argv))

if isValidOp(sys.argv[1]) == False:
	print("Invalid operation")
	sys.exit()
	
if isValidCmd(sys.argv[2]) == False:
	print("invalid command")
	sys.exit()

cmd_block = {
    "op" : sys.argv[1],
    "cmd" : sys.argv[2],
    "value" : sys.argv[3]
}


# Create a TCP/IP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Connect the socket to the port where the server is listening
server_address = ('localhost', 5322)
print(server_address)
sock.settimeout(5.0)
sock.connect(server_address)


try:
    
    # Send data
    message = json.dumps(cmd_block)
    print( message)
    sock.sendall(bytes(message,'ascii'))

    # Look for the response
    amount_received = 0
    
#    while amount_received < 5:
    eolr = False
    while eolr == False:
        data = sock.recv(100)
        sdata = str(data,'ascii')
        print( sdata)
        if endOfLine in sdata:
            eolr = True

#break

finally:
    print("closing socket")
    sock.close()