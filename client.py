import socket
import sys
import json

# Create a TCP/IP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Connect the socket to the port where the server is listening
server_address = ('localhost', 5322)
print(server_address)
sock.connect(server_address)
cmd_block = {
    "op" : "get",
    "cmd" : "ditherevery",
    "value" : "8"
}

try:
    
    # Send data
    message = json.dumps(cmd_block)
    print( message)
    sock.sendall(bytes(message,'ascii'))

    # Look for the response
    amount_received = 0
    amount_expected = len(message)
    
    while amount_received < 5:
        data = sock.recv(100)
        amount_received += len(data)
        print( data)

finally:
    print("closing socket")
    sock.close()