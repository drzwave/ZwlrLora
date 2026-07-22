#!/usr/bin/env python3
"""
Send a Meshtastic position (location) request to a node over the LoRa mesh,
wait for the response, and print the resulting location.

Requires:
    pip install meshtastic

Usage:
    python meshtastic_location_request.py --dest !aabbccdd
    python meshtastic_location_request.py --dest !aabbccdd --port /dev/ttyUSB0 --timeout 90

Notes:
    --dest is the target node's ID (shown as !xxxxxxxx in the Meshtastic app,
    or use "^all" to broadcast to the whole mesh — though most nodes only
    reply to a direct request).
    If --port is omitted, the library auto-detects a connected serial device.
"""

import argparse
import sys
import time

from pubsub import pub
import meshtastic
import meshtastic.serial_interface

position_received = False
response_data = None
response_from = None


def on_receive(packet, interface):
    """Called for every packet received from the mesh."""
    global position_received, response_data, response_from

    decoded = packet.get("decoded", {})
    if decoded.get("portnum") != "POSITION_APP":
        return

    position_received = True
    response_data = decoded.get("position", {})
    response_from = packet.get("fromId", "unknown")


def on_connection_established(interface, topic=pub.AUTO_TOPIC):
    print("Connected to local Meshtastic device.")


def print_position(from_id, position):
    lat = position.get("latitude")
    lon = position.get("longitude")
    alt = position.get("altitude")
    ts = position.get("time")

    print(f"\nLocation response received from {from_id}:")
    if lat is not None and lon is not None:
        print(f"  Latitude:  {lat}")
        print(f"  Longitude: {lon}")
    else:
        print("  No lat/lon in response (node may not have a GPS fix).")
    if alt is not None:
        print(f"  Altitude:  {alt} m")
    if ts is not None:
        print(f"  Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))}")
    print(f"  Raw payload: {position}")


def main():
    parser = argparse.ArgumentParser(
        description="Request a node's location over the Meshtastic LoRa mesh."
    )
    parser.add_argument(
        "--dest", "-d", required=True,
        help="Destination node ID, e.g. !aabbccdd"
    )
    parser.add_argument(
        "--port", "-p", default=None,
        help="Serial port of the local Meshtastic device (auto-detected if omitted)"
    )
    parser.add_argument(
        "--timeout", "-t", type=int, default=6,
        help="Seconds to wait for a response before giving up (default: 60)"
    )
    args = parser.parse_args()

    pub.subscribe(on_receive, "meshtastic.receive")
    pub.subscribe(on_connection_established, "meshtastic.connection.established")

    print("Connecting to local Meshtastic device...")
    try:
        interface = meshtastic.serial_interface.SerialInterface(devPath=args.port)
    except Exception as e:
        print(f"Failed to connect to Meshtastic device: {e}")
        sys.exit(1)

    try:
        #node = interface.getNode(args.dest, requestChannels=False) #this doesn't work
        node = interface.getNode(args.dest) #why does this take so long? It must setup other variables that are needed for SendPosition
        #node.requestPosition() # this is apparently not a valid object.
 
        try:
            while(True):
                print(f"Requesting position from {args.dest} ...")
                interface.sendPosition(destinationId=args.dest,wantResponse=True,wantAck=True)

                start = time.time()
                while not position_received and (time.time() - start) < args.timeout:
                    time.sleep(0.5)

                if position_received:
                    print_position(response_from, response_data)
                else:
                    print(f"No location response received within {args.timeout} seconds.")
                    print("The target node may be offline, out of range, or lack a GPS fix.")
                    break
                time.sleep(60*2) # cannot ask for the position more than every 3 minutes?

        except KeyboardInterrupt:
            print("done")

    finally:
        interface.close()


if __name__ == "__main__":
    main()
