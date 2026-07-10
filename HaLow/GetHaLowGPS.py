''' test program to fetch the GPS coordinates via WiFi/HaLow.
'''

import socket
import sys

def GetHaLowGPS(host='10.0.4.34', port=7007):
    # Create a TCP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        sock.connect((host, port))
        print(f"Connected to {host}:{port}")
        
        # Send a message
        message = b"PING"
        sock.sendall(message)
        print(f"Sent: {message.decode()}")
        
        # Receive a response (up to 4096 bytes)
        data = sock.recv(4096)
        print(f"Received: {data.decode()}")
        
        # Send a message
        message = b"TIME"
        sock.sendall(message)
        print(f"Sent: {message.decode()}")
        
        # Receive a response (up to 4096 bytes)
        data = sock.recv(4096)
        print(f"Received: {data.decode()}")
        
        # Send a message
        message = b"GPS"
        sock.sendall(message)
        print(f"Sent: {message.decode()}")
        
        # Receive a response (up to 4096 bytes)
        data = sock.recv(4096)
        print(f"Received: {data.decode()}")
        
    except ConnectionRefusedError:
        print(f"Could not connect to {host}:{port} — is the server running?")
    except socket.timeout:
        print("Connection timed out.")
    finally:
        sock.close()

if __name__ == "__main__":
    HOST = '10.0.4.39'
    if len(sys.argv) > 1:
        HOST=sys.argv[1]
    GetHaLowGPS(host=HOST)
