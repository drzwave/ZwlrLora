#!/usr/bin/env python3
"""
Read NMEA sentences from a u-blox SAM-M8Q GPS receiver over a serial (UART) connection.

Wiring (typical, e.g. Raspberry Pi):
    SAM-M8Q VCC -> 3.3V
    SAM-M8Q GND -> GND
    SAM-M8Q TX  -> Pi RX (GPIO15 / pin 10)
    SAM-M8Q RX  -> Pi TX (GPIO14 / pin 8)   [optional, only needed to send config commands]

Default UART baud rate for the SAM-M8Q is 9600 (u-blox default).

Requires:
    pip install pyserial
"""

import serial
import time
import getNema

# ----------------------------------------------------------------------
# Configuration - adjust to match your setup
# ----------------------------------------------------------------------
SERIAL_PORT = "/dev/ttyS0"   # e.g. "/dev/ttyUSB0", "/dev/ttyAMA0", or "COM3" on Windows
BAUD_RATE = 9600                # SAM-M8Q default
TIMEOUT_S = 1.0

# ----------------------------------------------------------------------

class getNema:

    def __init__(self):
        try:
            self.ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=TIMEOUT_S)
        except serial.SerialException as e:
            print(f"Could not open serial port {SERIAL_PORT}: {e}")
        print(f"Listening on {SERIAL_PORT} at {BAUD_RATE} baud. Press Ctrl+C to stop.\n")

    def GetN(self):

        while(True):
            try:
                raw_line = self.ser.readline()
            except serial.SerialException as e:
                print(f"Serial read error: {e}")
                time.sleep(1)
                continue

            if not raw_line:
                continue  # timeout with no data

            line = raw_line.decode("ascii", errors="replace").strip()
            if not line.startswith("$"):
                continue  # not a valid NMEA sentence

            sentence_type = line[3:6]  # e.g. GGA, RMC, GSV
            if sentence_type == "GGA":  # Fix data
                return(line)    # found the NEMA sentence with the GPS coordinates, exit

if __name__ == "__main__":
    try:
        dev=getNema()
        while(True):
            rtn=getNema.GetN(dev)
            print(rtn)
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        dev.ser.close()
