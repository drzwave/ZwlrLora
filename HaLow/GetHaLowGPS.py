''' test program to fetch the GPS coordinates via WiFi/HaLow.
'''

import socket
import sys
import time
from datetime import datetime

def GetHaLowGPS(host='192.168.0.30', port=7007):
    ''' Open a TCP socket and send 'GPS' to the host IP address.
        The host should reply with the NEMA string from a GPS receiver.
    '''
    # Create a TCP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        sock.connect((host, port))
        print(f"Connected to {host}:{port}")
        
        ''' don't need this anymore
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
        '''

        # request the GPS NEMA string
        message = b"GPS"
        sock.sendall(message)
        #print(f"Sent: {message.decode()}")
        
        # Receive a response (up to 4096 bytes)
        data = sock.recv(4096)
        #print(f"Received: {data.decode()}")
        return data.decode()
 
    except ConnectionRefusedError:
        print(f"Could not connect to {host}:{port} — is the server running?")
    except socket.timeout:
        print("Connection timed out.")
    finally:
        sock.close()

if __name__ == "__main__":
    HOST = '192.168.0.30'
    if len(sys.argv) > 1: # use the IP address on the command line
        HOST=sys.argv[1]
    f = open("HaLow.csv","a")
    print(f"Time,Lat,Lon,Alt,Sats,Zero, GetHaLowGPS.py {datetime.now()}", file=f)

    try:
        while(True):
            time.sleep(3)
            nemastr = GetHaLowGPS(host=HOST)
            if nemastr:
                print(nemastr)
                nemalist=nemastr.split(',')
                print(nemalist)
                if "GGA" in nemalist[0]: # valid string
                    if int(nemalist[7])>3: # must have more than 3 satelites or there is no fix
                        if len(nemalist[2])>3 and len(nemalist[4])>3: # then there are numbers for lat/lon
                            nemalat=nemalist[2]
                            lat = float(nemalat[0:2]) + (float(nemalat[2:])/60)
                            if 'S' in nemalist[3]: lat=-lat
                            nemalon=nemalist[4]
                            lon = float(nemalon[0:3]) + (float(nemalon[3:])/60)
                            if 'W' in nemalist[5]: lon=-lon
                            alt=float(nemalist[9])
                            print(f"sats={nemalist[7]} Lon={lon} Lat={lat} Alt={alt}")
                            now=datetime.now()
                            print(f"{now.time()},{lat:.6f},{lon:.6f},{alt:.2f},{nemalist[7]},0",file=f)
    except KeyboardInterrupt:
        print("done")

