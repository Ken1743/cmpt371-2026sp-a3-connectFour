#!/usr/bin/env python3
"""Client entry point: wires UI and network."""

import tkinter as tk

from client_network import NetworkClient
from client_ui import App


def main() -> None:
    # Start GUI and connect UI callbacks to network layer.
    root = tk.Tk()
    ui = App(root)

    # Keep the network client in a small container so callbacks can update it
    network_client = {"client": None}

    def on_connect(host: str, port: int, name: str) -> bool:
        # Create network client and connect to server.
        client = NetworkClient(
            host,
            port,
            on_message=lambda message: ui.msg_queue.put(message),
            on_error=lambda err: ui.msg_queue.put({"type": "error", "message": err}),
        )
        client.connect(name)
        network_client["client"] = client
        return True

    def on_disconnect() -> None:
        # Close network connection if it exists.
        client = network_client.get("client")
        if client:
            client.close()
            network_client["client"] = None

    def on_move(column: int) -> None:
        # Send move to server through network client.
        client = network_client.get("client")
        if client:
            client.send_move(column)

    def on_close() -> None:
        # Ensure connection is closed when window closes.
        on_disconnect()
        root.destroy()

    # Register UI callbacks
    ui.set_handlers(on_connect, on_disconnect, on_move)
    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
