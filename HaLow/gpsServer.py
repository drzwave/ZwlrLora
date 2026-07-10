#!/usr/bin/env python3
"""
Simple TCP server that listens on port 7007, reads a text command
from a connecting client, and sends back a text response.

Usage:
    python3 tcp_command_server.py

Test it (in another terminal):
    printf "PING\n" | nc localhost 7007
    printf "TIME\n" | nc localhost 7007
"""

import socket
import datetime
import getNema

HOST = "0.0.0.0"   # listen on all interfaces
PORT = 7007
BUFFER_SIZE = 4096


def handle_command(command: str) -> str:
    """
    Decide what to send back based on the received command.
    """
    cmd = command.strip().upper()

    if cmd == "PING":
        return "PONG"
    elif cmd == "TIME":
        return datetime.datetime.now().isoformat()
    elif cmd == "GPS":
        dev=getNema.getNema()
        rtn=dev.GetN()
        print(rtn)
        return(rtn)
    elif cmd == "":
        return "ERROR: empty command"
    else:
        return f"ERROR: unknown command '{command.strip()}'"


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
        # Allow quick restarts without "Address already in use" errors
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((HOST, PORT))
        server_sock.listen()
        print(f"Listening on {HOST}:{PORT} ... (Ctrl+C to stop)")

        try:
            while True:
                conn, addr = server_sock.accept()
                print(f"Connection from {addr}")
                while True:
                    data = conn.recv(BUFFER_SIZE)
                    if not data:
                        print("Client Disconnected")
                        break

                    command = data.decode("utf-8", errors="replace")
                    print(f"Received: {command!r}")

                    response = handle_command(command)
                    conn.sendall((response + "\n").encode("utf-8"))
                    print(f"Sent: {response!r}")

        except KeyboardInterrupt:
            print("\nShutting down server.")


if __name__ == "__main__":
    main()
