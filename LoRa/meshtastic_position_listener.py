#!/usr/bin/env python3
"""
Meshtastic Position Listener

Connects to a Meshtastic device (default: USB serial) and prints GPS
coordinates whenever a position report is received from any node on
the mesh.

Requires the official meshtastic python library:
    pip install meshtastic

Usage:
    python meshtastic_position_listener.py                # auto-detect serial device
    python meshtastic_position_listener.py --port /dev/ttyUSB0
    python meshtastic_position_listener.py --tcp 192.168.1.50   # connect over WiFi/TCP instead
"""

import argparse
import time
from datetime import datetime

from pubsub import pub
import meshtastic
import meshtastic.serial_interface
import meshtastic.tcp_interface


def on_position_receive(packet, interface):
    """Callback fired for every received packet; filters for position reports."""
    try:
        decoded = packet.get("decoded", {})
        if decoded.get("portnum") != "POSITION_APP":
            return  # not a position report, ignore

        f = open("LoRa.csv","a")
        position = decoded.get("position", {})
        lat = position.get("latitude")
        lon = position.get("longitude")
        alt = position.get("altitude")
        sats = position.get("sats_in_view")

        from_id = packet.get("fromId", packet.get("from", "unknown"))
        node_info = interface.nodes.get(from_id) if hasattr(interface, "nodes") else None
        long_name = None
        if node_info:
            long_name = node_info.get("user", {}).get("longName")

        label = f"{long_name} ({from_id})" if long_name else from_id
        timestamp = time.strftime("%H:%M:%S")

        if lat is not None and lon is not None:
            alt_str = f", alt={alt}m" if alt is not None else ""
            print(f"[{timestamp}] {label}: lat={lat:.6f}, lon={lon:.6f}{alt_str}")
        else:
            print(f"[{timestamp}] {label}: position packet received but no lat/lon set")

        now=datetime.now()
        print(f"{now.time()},{lat:.6f},{lon:.6f},{alt:.2f},{sats},0",file=f)
        
    except Exception as e:
        print(f"Error processing packet: {e}")


def on_connection_established(interface, topic=pub.AUTO_TOPIC):
    print("Connected to Meshtastic device. Listening for position reports...\n")


def main():
    f = open("LoRa.csv","a")
    print(f"Time,Lat,Lon,Alt,Sats,Zero, meshtastic_position_listener.py {datetime.now()}", file=f)
    f.close()

    parser = argparse.ArgumentParser(description="Print GPS coordinates from Meshtastic position reports")
    parser.add_argument("--port", help="Serial device path (e.g. /dev/ttyUSB0 or COM3). "
                                        "If omitted, auto-detects.")
    parser.add_argument("--tcp", help="Connect via TCP/WiFi instead of serial, e.g. --tcp 192.168.1.50")
    args = parser.parse_args()

    pub.subscribe(on_position_receive, "meshtastic.receive.position")
    pub.subscribe(on_connection_established, "meshtastic.connection.established")

    if args.tcp:
        print(f"Connecting to Meshtastic device over TCP at {args.tcp}...")
        interface = meshtastic.tcp_interface.TCPInterface(hostname=args.tcp)
    else:
        print("Connecting to Meshtastic device via serial...")
        interface = meshtastic.serial_interface.SerialInterface(devPath=args.port)

    print("Press Ctrl+C to exit.\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        interface.close()


if __name__ == "__main__":
    main()
