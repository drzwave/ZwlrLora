#!/usr/bin/env python3
"""
Simple TCP server that listens on port 7007, reads a text command
from a connecting client, and sends back a text response.

Robustness features:
- If the listening socket or a connection errors out for any reason,
  the server logs it, cleans up, and reopens the listening socket
  rather than crashing.
- A short backoff is applied between restart attempts so a persistent
  failure (e.g. port in use) doesn't spin the CPU.
- The only way to actually exit the program is Ctrl+C (KeyboardInterrupt).

Usage:
    python3 gpsServer.py

Test it (in another terminal):
    printf "PING\n" | nc localhost 7007
    printf "TIME\n" | nc localhost 7007
    printf "GPS\n"  | nc localhost 7007
"""

import socket
import datetime
import logging
import time

import getNema

HOST = "0.0.0.0"   # listen on all interfaces
PORT = 7007
BUFFER_SIZE = 4096

# Seconds to wait before trying to reopen the listening socket after a
# failure (e.g. bind() failing because the port hasn't been released yet).
RESTART_BACKOFF_SECONDS = 2

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("gpsServer")


def handle_command(command: str) -> str:
    """
    Decide what to send back based on the received command.
    Never raises: any internal error is turned into an ERROR response
    so a single bad command can't take down the connection or server.
    """
    cmd = command.strip().upper()

    try:
        if cmd == "PING":
            return "PONG"
        elif cmd == "TIME":
            return datetime.datetime.now().isoformat()
        elif cmd == "GPS":
            dev = getNema.getNema()
            rtn = dev.GetN()
            log.info("GPS response: %r", rtn)
            return rtn
        elif cmd == "":
            return "ERROR: empty command"
        else:
            return f"ERROR: unknown command '{command.strip()}'"
    except Exception as exc:
        log.exception("Error while handling command %r", command)
        return f"ERROR: internal error handling command: {exc}"


def handle_client(conn: socket.socket, addr) -> None:
    """
    Service a single client connection until it disconnects or an
    error occurs. Errors here are caught by the caller so they don't
    bring down the whole server.
    """
    with conn:
        conn.settimeout(None)
        while True:
            data = conn.recv(BUFFER_SIZE)
            if not data:
                log.info("Client %s disconnected", addr)
                break

            try:
                command = data.decode("utf-8", errors="replace")
            except Exception:
                log.exception("Failed to decode data from %s", addr)
                continue

            response = handle_command(command)

            try:
                conn.sendall((response + "\n").encode("utf-8"))
            except (BrokenPipeError, ConnectionResetError, OSError):
                log.warning("Lost connection to %s while sending response", addr)
                break


def serve_forever() -> None:
    """
    Open the listening socket and accept connections until an error
    occurs, at which point this function returns so the caller can
    decide whether to retry. KeyboardInterrupt is allowed to propagate
    so the whole program can exit cleanly.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((HOST, PORT))
        server_sock.listen()
        log.info("Listening on %s:%s ... (Ctrl+C to stop)", HOST, PORT)

        while True:
            conn, addr = server_sock.accept()
            log.info("Connection from %s", addr)
            try:
                handle_client(conn, addr)
            except KeyboardInterrupt:
                raise
            except Exception:
                log.exception("Unhandled error while servicing client %s", addr)
                # Loop back and keep accepting new connections.


def main() -> None:
    try:
        while True:
            try:
                serve_forever()
            except KeyboardInterrupt:
                raise
            except Exception:
                log.exception(
                    "Server loop crashed; reopening socket in %s second(s)",
                    RESTART_BACKOFF_SECONDS,
                )
                time.sleep(RESTART_BACKOFF_SECONDS)
    except KeyboardInterrupt:
        log.info("Shutting down server.")


if __name__ == "__main__":
    main()
