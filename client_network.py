#!/usr/bin/env python3
#Network layer for Connect Four client.

import json
import socket
import threading
from typing import Callable, Optional, Any


def send_json_line(connection: socket.socket, obj: dict) -> None:
    #Send one JSON object followed by newline.
    # Convert dict -> JSON line and send over TCP
    data = json.dumps(obj, ensure_ascii=True) + "\n"
    connection.sendall(data.encode("utf-8"))


class NetworkClient:
    #Simple TCP client that reads JSON lines in a background thread.

    def __init__(self, host: str, port: int, on_message: Callable[[dict], None], on_error: Callable[[str], None]) -> None:
        self.host = host
        self.port = port
        self.on_message = on_message
        self.on_error = on_error
        self.connection: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None

    def connect(self, name: str) -> None:
        #Connect to server and send join message.
        # Open TCP connection and send join handshake
        self.connection = socket.create_connection((self.host, self.port), timeout=5)
        self.connection.settimeout(None)
        send_json_line(self.connection, {"type": "join", "name": name})
        self._thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._thread.start()

    def send_move(self, column: int) -> None:
        #Send a move request to the server.
        # Send selected column to server
        if not self.connection:
            return
        send_json_line(self.connection, {"type": "move", "column": column})

    def close(self) -> None:
        #Close the connection.
        # Tell server we quit, then close socket
        if not self.connection:
            return
        try:
            send_json_line(self.connection, {"type": "quit"})
            self.connection.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.connection.close()
        except OSError:
            pass
        self.connection = None

    def _reader_loop(self) -> None:
        #Read lines from server and forward to callback.
        # Background reader thread: parse JSON and call on_message
        try:
            assert self.connection is not None
            file_obj = self.connection.makefile("r", encoding="utf-8", newline="\n")
            for line in file_obj:
                line = line.strip()
                if line:
                    try:
                        message = json.loads(line)
                        self.on_message(message)
                    except Exception as exc:  # noqa: BLE001
                        self.on_error(f"invalid_json: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.on_error(str(exc))
