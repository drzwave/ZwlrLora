#!/usr/bin/env python3
"""
Get GPS location from a Meshtastic node.

Install dependency first:
    pip install meshtastic

Usage:
    python get_location.py                  # auto-detect serial device
    python get_location.py --port /dev/ttyUSB0
    python get_location.py --host 192.168.1.50   # TCP/WiFi node
"""

import argparse
import sys
import time

import meshtastic
import meshtastic.serial_interface
import meshtastic.tcp_interface


def get_interface(args):
    if args.host:
        return meshtastic.tcp_interface.TCPInterface(hostname=args.host)
    elif args.port:
        return meshtastic.serial_interface.SerialInterface(devPath=args.port)
    else:
        # Auto-detect the first serial device
        return meshtastic.serial_interface.SerialInterface()


def format_position(node_id, node):
    pos = node.get("position", {})
    user = node.get("user", {})
    name = user.get("longName", user.get("shortName", node_id))

    lat = pos.get("latitude")
    lon = pos.get("longitude")
    alt = pos.get("altitude")
    ts = pos.get("time")

    if lat is None or lon is None:
        return f"{name} ({node_id}): no GPS fix available"

    line = f"{name} ({node_id}): lat={lat:.6f}, lon={lon:.6f}"
    if alt is not None:
        line += f", alt={alt}m"
    if ts:
        line += f", updated={time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))}"
    return line


def main():
    parser = argparse.ArgumentParser(description="Fetch GPS location from Meshtastic node(s)")
    parser.add_argument("--port", help="Serial port, e.g. /dev/ttyUSB0 or COM3")
    parser.add_argument("--host", help="IP/hostname for TCP-connected node")
    parser.add_argument("--node", help="Specific node ID (e.g. !a1b2c3d4) to query; default = all known nodes")
    parser.add_argument("--wait", type=float, default=3.0,
                         help="Seconds to wait for the connection/node DB to populate")
    args = parser.parse_args()

    print("Connecting to node...")
    iface = get_interface(args)

    try:
        # Give it a moment to receive the node database
        time.sleep(args.wait)

        # Local connected node's own info
        my_info = iface.getMyNodeInfo()
        if my_info:
            my_id = my_info.get("user", {}).get("id", "local")
            print("\n--- Locally connected node ---")
            print(format_position(my_id, my_info))

        # All nodes heard on the mesh (each may have a position)
        print("\n--- Known mesh nodes ---")
        nodes = iface.nodes or {}
        if not nodes:
            print("No nodes found yet. Try increasing --wait.")
        for node_id, node in nodes.items():
            if (args.node is None) or (args.node in node_id):
                print(format_position(node_id, node))

    finally:
        iface.close()


if __name__ == "__main__":
    main()
