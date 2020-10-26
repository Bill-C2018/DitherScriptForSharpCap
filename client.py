import socket
import sys
import json

HOST_ADDRESS = "localhost"
HOST_PORT = 5322
TIMEOUT = 5.0

'''
=============================================================================
do not edit anything below here
=============================================================================
'''

endOfLine = "\r\n"
valid_cmds = ["ditherevery", "waitfornextframe", "raonly", "settletarget", "settledelay", "settlemax", "maxpixels", "ditherstring"]
valid_ops = ["get", "set"]
data = None


def print_valid_cmds():
    for c in valid_cmds:
        msg = c + "\r\n"
        print (msg)

        
def print_valid_ops():
    for o in valid_ops:
        msg = o + "\r\n"
        print (msg)

        
def is_valid_cmd(cmd):

    for x in valid_cmds:
        if x == cmd:
            return True
        
    return False


def is_valid_op(op):    

    for x in valid_ops:
        if x == op:
            return True
        
    return False

    
def validate_cmd_line(data):
    print(str(sys.argv))
    
    if is_valid_op(sys.argv[1]) == False:
        print("Invalid operation")
        print_valid_ops()
        sys.exit()
        
    if is_valid_cmd(sys.argv[2]) == False:
        print("invalid command")
        print_valid_cmds()
        sys.exit()
    
    if sys.argv[1] == "get":
        if(len(sys.argv) < 4):
            data = 0
        else:
            data = syst.argv[3]
            
    else:
        if(len(sys.argv) < 4):
            print("Value is required for set operation")
            sys.exit()


def connect_and_transmit(cmd_block):
    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # Connect the socket to the port where the server is listening
    server_address = (HOST_ADDRESS, HOST_PORT)
    print(server_address)
    sock.settimeout(TIMEOUT)
    sock.connect(server_address)
    
    try:
        
        # Send data
        message = json.dumps(cmd_block)
        print(message)
        sock.sendall(bytes(message, 'ascii'))

        # Recieve response
        eolr = False
        while eolr == False:
            data = sock.recv(255)
            sdata = str(data, 'ascii')
            print(sdata)
            if endOfLine in sdata:
                eolr = True

    finally:
        print("closing socket")
        sock.close()
        
'''
===============================================================================
Main functionality
===============================================================================
'''
            
validate_cmd_line(data)
        
cmd_block = {
    "op" : sys.argv[1],
    "cmd" : sys.argv[2],
    "value" : data
}

connect_and_transmit(cmd_block)
