''' test program to fetch the GPS coordinates via WiFi/HaLow.
'''

import socket
import sys
import time
from datetime import datetime

def GetHaLowGPS(host='192.168.0.30', port=7007):
    ''' Open a TCP socket and send 'GPS' to the host IP address.
        The host should reply with the NMEA string from a GPS receiver.
    '''
    # Create a TCP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10.0) # set a timeout of 10s

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

        # request the GPS NMEA string
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
        print("Socket Connection timed out.")
    except TimeoutError:
        print("TimeoutError.")
    except KeyboardInterrupt:
        print("exit")
    except Exception as e:
        print(f"Exception:{e}")
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
            time.sleep(7)
            NMEAstr = GetHaLowGPS(host=HOST)
            if NMEAstr:
                print(NMEAstr)
                NMEAlist=NMEAstr.split(',')
                print(NMEAlist)
                if "GGA" in NMEAlist[0]: # valid string
                    if int(NMEAlist[7])>3: # must have more than 3 satelites or there is no fix
                        if len(NMEAlist[2])>3 and len(NMEAlist[4])>3: # then there are numbers for lat/lon
                            NMEAlat=NMEAlist[2]
                            lat = float(NMEAlat[0:2]) + (float(NMEAlat[2:])/60)
                            if 'S' in NMEAlist[3]: lat=-lat
                            NMEAlon=NMEAlist[4]
                            lon = float(NMEAlon[0:3]) + (float(NMEAlon[3:])/60)
                            if 'W' in NMEAlist[5]: lon=-lon
                            alt=float(NMEAlist[9])
                            print(f"sats={NMEAlist[7]} Lon={lon} Lat={lat} Alt={alt}")
                            now=datetime.now()
                            print(f"{now.time()},{lat:.6f},{lon:.6f},{alt:.2f},{NMEAlist[7]},0",file=f)
    except Exception as e:
        print(f"Exception-{e}")
    except KeyboardInterrupt:
        print("Done")

