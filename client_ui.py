#!/usr/bin/env python3
"""Connect Four GUI client (Tkinter).
- click a column to drop a piece
- server decides if move is valid
- GUI redraws board when state arrives
"""

import queue
import tkinter as tk
from pathlib import Path
from typing import Optional
from tkinter.scrolledtext import ScrolledText


ROWS = 6
COLS = 7
BOARD_W = 420
BOARD_H = 360

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
ICON_P1 = ASSETS_DIR / "icon1.png"
ICON_P2 = ASSETS_DIR / "icon2.png"
CARD_P1 = ASSETS_DIR / "p1.png"
CARD_P2 = ASSETS_DIR / "p2.png"

# UI constants
COLOR_BG = "#b7e0b7"
COLOR_TEXT = "#6b3f1d"
COLOR_INPUT_BG = "#8ccf8c"
COLOR_LOG_BG = "#dff3df"
COLOR_TURN_HIGHLIGHT = "#f6e7a2"
COLOR_CELL_HIGHLIGHT = "#f6e7a2"
COLOR_BOARD_BG = "#a8794f"
COLOR_GRID = "#6a4a2a"
COLOR_PIECE_P1_BG = "#9fd7ff"
COLOR_PIECE_P2_BG = "#ffb3c7"


class App:
    def __init__(self, root: tk.Tk) -> None:
        # Input: root (Tk). Output: none.
        # Build GUI and initialize state.
        self.root = root
        self.root.title("Connect Four")
        self.root.resizable(False, False)

        # network
        self.msg_queue: queue.Queue[str] = queue.Queue()
        self.connected = False
        self.on_connect = None
        self.on_disconnect = None
        self.on_move = None

        # game state
        self.player_id: Optional[int] = None
        self.turn: int = 1
        self.over = False
        self.board = [[0 for _ in range(COLS)] for _ in range(ROWS)]
        self.cursor_col = 0
        self._cell_items = [[None for _ in range(COLS)] for _ in range(ROWS)]
        self._highlight_item = None
        self._grid_drawn = False
        self.piece_image_player1 = None
        self.piece_image_player2 = None
        self.profile_image_player1 = None
        self.profile_image_player2 = None

        self._build_ui()
        self._poll_msgs()
        self._load_icons()

    def _build_ui(self) -> None:
        # Input: none. Output: none.
        # Build all GUI widgets.
        # Main container frame
        frm = tk.Frame(self.root, bg=COLOR_BG)
        frm.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.root.configure(bg=COLOR_BG)

        # Layout: left panel | center (board) | right panel
        frm.columnconfigure(1, weight=1)

        left = tk.Frame(frm, bg=COLOR_BG, width=220, height=BOARD_H)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 10))
        left.pack_propagate(False)

        center = tk.Frame(frm, bg=COLOR_BG)
        center.grid(row=0, column=1, sticky="nsew")
        center.columnconfigure(0, weight=1)

        right = tk.Frame(frm, bg=COLOR_BG, width=220, height=BOARD_H)
        right.grid(row=0, column=2, sticky="ns", padx=(10, 0))
        right.pack_propagate(False)

        # Left player panel (name + image)
        self.player1_name_var = tk.StringVar(value="")
        self.player1_base_name = ""
        self.player1_panel = tk.Frame(left, bg=COLOR_BG)
        self.player1_panel.pack(pady=(60, 8), padx=6, fill="x")
        self.player1_name_label = tk.Label(self.player1_panel, textvariable=self.player1_name_var, bg=COLOR_BG, fg=COLOR_TEXT, font=("Helvetica", 16, "bold"))
        self.player1_name_label.pack(pady=(4, 6))
        self.player1_image_label = tk.Label(self.player1_panel, bg=COLOR_BG)
        self.player1_image_label.pack(padx=10, pady=(0, 10))

        # Right player panel (name + icon)
        self.player2_name_var = tk.StringVar(value="")
        self.player2_base_name = ""
        self.player2_panel = tk.Frame(right, bg=COLOR_BG)
        self.player2_panel.pack(pady=(60, 8), padx=6, fill="x")
        self.player2_name_label = tk.Label(self.player2_panel, textvariable=self.player2_name_var, bg=COLOR_BG, fg=COLOR_TEXT, font=("Helvetica", 16, "bold"))
        self.player2_name_label.pack(pady=(4, 6))
        self.player2_image_label = tk.Label(self.player2_panel, bg=COLOR_BG)
        self.player2_image_label.pack(padx=10, pady=(0, 10))

        # Controls instruction (always visible on right)
        ctrl_text = "Control\n\u2190  \u2192 : Select column\nspace : Place"
        self.ctrl_label = tk.Label(
            right,
            text=ctrl_text,
            bg=COLOR_BG,
            fg=COLOR_TEXT,
            font=("Helvetica", 12, "bold"),
            justify="left",
        )
        self.ctrl_label.pack(side="bottom", anchor="se", padx=10, pady=10)

        top = tk.Frame(center, bg=COLOR_BG)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(7, weight=1)

        tk.Label(top, text="Host", bg=COLOR_BG, fg=COLOR_TEXT).grid(row=0, column=0, sticky="w")
        self.host_var = tk.StringVar(value="127.0.0.1")
        self.host_entry = tk.Entry(
            top,
            textvariable=self.host_var,
            width=16,
            bg=COLOR_INPUT_BG,
            fg=COLOR_TEXT,
            insertbackground=COLOR_TEXT,
            disabledbackground=COLOR_INPUT_BG,
            disabledforeground=COLOR_TEXT,
            relief="flat",
            highlightthickness=0,
            bd=0,
        )
        self.host_entry.grid(row=0, column=1, padx=4)

        tk.Label(top, text="Port", bg=COLOR_BG, fg=COLOR_TEXT).grid(row=0, column=2, sticky="w")
        self.port_var = tk.IntVar(value=6000)
        self.port_entry = tk.Entry(
            top,
            textvariable=self.port_var,
            width=6,
            bg=COLOR_INPUT_BG,
            fg=COLOR_TEXT,
            insertbackground=COLOR_TEXT,
            disabledbackground=COLOR_INPUT_BG,
            disabledforeground=COLOR_TEXT,
            relief="flat",
            highlightthickness=0,
            bd=0,
        )
        self.port_entry.grid(row=0, column=3, padx=4)

        tk.Label(top, text="Name", bg=COLOR_BG, fg=COLOR_TEXT).grid(row=0, column=4, sticky="w")
        self.name_var = tk.StringVar(value="player")
        self.name_entry = tk.Entry(
            top,
            textvariable=self.name_var,
            width=12,
            bg=COLOR_INPUT_BG,
            fg=COLOR_TEXT,
            insertbackground=COLOR_TEXT,
            disabledbackground=COLOR_INPUT_BG,
            disabledforeground=COLOR_TEXT,
            relief="flat",
            highlightthickness=0,
            bd=0,
        )
        self.name_entry.grid(row=0, column=5, padx=4)

        self.connect_btn = tk.Button(
            top,
            text="Connect",
            command=self._handle_connect,
            bg=COLOR_BG,
            fg=COLOR_TEXT,
            activebackground=COLOR_BG,
            activeforeground=COLOR_TEXT,
            disabledforeground=COLOR_TEXT,
            relief="flat",
            bd=0,
            highlightthickness=0,
            highlightbackground=COLOR_BG,
            highlightcolor=COLOR_BG,
            takefocus=0,
        )
        self.connect_btn.grid(row=0, column=6, padx=4)
        self.disconnect_btn = tk.Button(
            top,
            text="Disconnect",
            command=self._handle_disconnect,
            bg=COLOR_BG,
            fg=COLOR_TEXT,
            activebackground=COLOR_BG,
            activeforeground=COLOR_TEXT,
            disabledforeground=COLOR_TEXT,
            relief="flat",
            bd=0,
            highlightthickness=0,
            highlightbackground=COLOR_BG,
            highlightcolor=COLOR_BG,
            takefocus=0,
        )
        self.disconnect_btn.grid(row=0, column=7, padx=4)

        self.status_var = tk.StringVar(value="Not connected")
        tk.Label(center, textvariable=self.status_var, bg=COLOR_BG, fg=COLOR_TEXT).grid(row=1, column=0, sticky="w", pady=(6, 6))

        # Board area (canvas)
        self.canvas = tk.Canvas(center, width=BOARD_W, height=BOARD_H, bg=COLOR_BOARD_BG, highlightthickness=0, bd=0)
        self.canvas.grid(row=2, column=0, sticky="nsew")
        # mouse click is disabled; use keyboard only

        self.log = ScrolledText(
            center,
            height=8,
            state="disabled",
            bg=COLOR_LOG_BG,
            fg=COLOR_TEXT,
            insertbackground=COLOR_TEXT,
            bd=0,
            highlightthickness=0,
        )
        self.log.grid(row=3, column=0, sticky="nsew", pady=(8, 0))

        center.rowconfigure(2, weight=1)

        self._draw_board()

        # Keyboard control: left/right to choose column, space to place piece
        self.root.bind_all("<Left>", self.on_left)
        self.root.bind_all("<Right>", self.on_right)
        self.root.bind_all("<space>", self.on_space)

        self._set_connected_ui(False)

    def _set_connected_ui(self, connected: bool) -> None:
        # Input: connected (bool). Output: none.
        # Enable/disable widgets based on connection state.
        state_entries = "disabled" if connected else "normal"
        self.host_entry.config(state=state_entries)
        self.port_entry.config(state=state_entries)
        self.name_entry.config(state=state_entries)
        if connected:
            self.connect_btn.config(state="disabled", bg=COLOR_BG, activebackground=COLOR_BG)
            self.disconnect_btn.config(state="normal", bg=COLOR_BG, activebackground=COLOR_BG)
        else:
            self.connect_btn.config(state="normal", bg=COLOR_BG, activebackground=COLOR_BG)
            self.disconnect_btn.config(state="disabled", bg=COLOR_BG, activebackground=COLOR_BG)
        self.connected = connected

    def log_msg(self, message: str) -> None:
        # Input: message (str). Output: none.
        # Append a line to the log box.
        """Append a line to the log box."""
        # Enable -> insert -> disable to keep read only
        self.log.configure(state="normal")
        self.log.insert("end", message + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _draw_board(self) -> None:
        # Input: none. Output: none.
        # Redraw the board based on current state.
        """Redraw the circles based on current board state."""
        # Draw grid only once, then only update pieces/highlight
        if not self._grid_drawn:
            self._draw_grid()
            self._grid_drawn = True

        # update highlight
        self._update_highlight()

        # update pieces
        for r in range(ROWS):
            for c in range(COLS):
                self._update_piece(r, c)

    def _draw_grid(self) -> None:
        # Input: none. Output: none.
        # Draw board background and grid lines once.
        # Cache canvas size for later coordinate math
        self.canvas.delete("all")
        self.canvas.update_idletasks()
        self._canvas_w = self.canvas.winfo_width()
        self._canvas_h = self.canvas.winfo_height()
        self._cell_w = self._canvas_w / COLS
        self._cell_h = self._canvas_h / ROWS

        # background
        self.canvas.create_rectangle(0, 0, self._canvas_w, self._canvas_h, outline="", fill=COLOR_BOARD_BG)

        # grid lines
        for c in range(COLS + 1):
            x = c * self._cell_w
            self.canvas.create_line(x, 0, x, self._canvas_h, fill=COLOR_GRID)
        for r in range(ROWS + 1):
            y = r * self._cell_h
            self.canvas.create_line(0, y, self._canvas_w, y, fill=COLOR_GRID)

    def _update_highlight(self) -> None:
        # Input: none. Output: none.
        # Update highlight rectangle position.
        # Highlight only on your turn
        if self.player_id is None or self.turn != self.player_id or self.over:
            if self._highlight_item is not None:
                self.canvas.delete(self._highlight_item)
                self._highlight_item = None
            return
        target_row = self._landing_row(self.cursor_col)
        if target_row is None:
            if self._highlight_item is not None:
                self.canvas.delete(self._highlight_item)
                self._highlight_item = None
            return
        x1 = self.cursor_col * self._cell_w
        y1 = target_row * self._cell_h
        x2 = (self.cursor_col + 1) * self._cell_w
        y2 = (target_row + 1) * self._cell_h
        if self._highlight_item is None:
            self._highlight_item = self.canvas.create_rectangle(x1, y1, x2, y2, outline="", fill=COLOR_CELL_HIGHLIGHT)
        else:
            self.canvas.coords(self._highlight_item, x1, y1, x2, y2)

    def _update_piece(self, row: int, column: int) -> None:
        # Input: row, column. Output: none.
        # Update a single cell piece drawing.
        # Remove old piece in this cell, then draw new one if needed
        x1 = column * self._cell_w + 8
        y1 = row * self._cell_h + 8
        x2 = (column + 1) * self._cell_w - 8
        y2 = (row + 1) * self._cell_h - 8
        value = self.board[row][column]

        # clear old item
        old = self._cell_items[row][column]
        if old is not None:
            for item in old:
                self.canvas.delete(item)
            self._cell_items[row][column] = None

        if value == 1 and self.piece_image_player1 is not None:
            oval = self.canvas.create_oval(x1, y1, x2, y2, fill=COLOR_PIECE_P1_BG, outline="")
            img = self.canvas.create_image((x1 + x2) / 2, (y1 + y2) / 2, image=self.piece_image_player1)
            self._cell_items[row][column] = (oval, img)
        elif value == 2 and self.piece_image_player2 is not None:
            oval = self.canvas.create_oval(x1, y1, x2, y2, fill=COLOR_PIECE_P2_BG, outline="")
            img = self.canvas.create_image((x1 + x2) / 2, (y1 + y2) / 2, image=self.piece_image_player2)
            self._cell_items[row][column] = (oval, img)

    def _load_icons(self) -> None:
        # Input: none. Output: none.
        # Load PNG images.
        # Piece icons are small; profile cards are bigger
        if not ICON_P1.exists() or not ICON_P2.exists():
            return
        # Use current canvas size for scaling
        self.canvas.update_idletasks()
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        size = int(min(w / COLS, h / ROWS) * 0.8)
        if size <= 0:
            return
        try:
            # Source images are 500x500, use subsample to scale down.
            scale = max(1, 500 // size)
            self.piece_image_player1 = tk.PhotoImage(file=str(ICON_P1)).subsample(scale, scale)
            self.piece_image_player2 = tk.PhotoImage(file=str(ICON_P2)).subsample(scale, scale)
        except Exception:
            self.piece_image_player1 = None
            self.piece_image_player2 = None

        # Load side panel images (p1.png / p2.png)
        # Fit to panel height (roughly board height)
        self.profile_image_player1 = self._fit_image(CARD_P1, 200, BOARD_H - 40)
        self.profile_image_player2 = self._fit_image(CARD_P2, 200, BOARD_H - 40)
        # do not show side images until players connect

    def _fit_image(self, path: Path, max_w: int, max_h: int):
        # Input: path, max_w, max_h. Output: PhotoImage or None.
        # Load an image and downscale to fit max size.
        if not path.exists():
            return None
        try:
            img = tk.PhotoImage(file=str(path))
            w = img.width()
            h = img.height()
            scale = max(1, max(w // max_w, h // max_h))
            if scale > 1:
                img = img.subsample(scale, scale)
            return img
        except Exception:
            return None

    def _handle_connect(self) -> None:
        # Input: none. Output: none.
        # Trigger connect callback and update UI state.
        # UI validates input, then calls network handler
        if self.connected:
            self.log_msg("Already connected")
            return
        if self.on_connect is None:
            self.log_msg("Connect handler not set")
            return
        host = self.host_var.get().strip()
        port = int(self.port_var.get())
        name = self.name_var.get().strip() or "player"
        self.status_var.set("Connecting...")
        try:
            ok = self.on_connect(host, port, name)
        except Exception as exc:  # noqa: BLE001
            ok = False
            self.log_msg(f"Connect error: {exc}")
        if ok:
            self.log_msg(f"Connecting to {host}:{port} as {name}")
            self.status_var.set("Connected. Waiting for welcome...")
            self._set_connected_ui(True)
            self.canvas.focus_set()
        else:
            self.status_var.set("Not connected")
            self._set_connected_ui(False)

    def _handle_disconnect(self) -> None:
        # Input: none. Output: none.
        # Trigger disconnect callback and reset UI state.
        # Always clear UI even if network close fails
        if self.on_disconnect is not None:
            try:
                self.on_disconnect()
            except Exception as exc:  # noqa: BLE001
                self.log_msg(f"Disconnect error: {exc}")
        self._reset_local_state()
        self._set_connected_ui(False)

    def disconnect(self) -> None:
        # Input: none. Output: none.
        # Deprecated: use _handle_disconnect (kept for compatibility).
        self._handle_disconnect()

    def _reset_local_state(self) -> None:
        # Input: none. Output: none.
        # Clear local UI state on disconnect.
        self.status_var.set("Disconnected")
        self.player_id = None
        self._reset_player_panels()
        self.board = [[0 for _ in range(COLS)] for _ in range(ROWS)]
        self._grid_drawn = False
        self._draw_board()

    def set_handlers(self, on_connect, on_disconnect, on_move) -> None:
        # Input: callbacks. Output: none.
        # Register callbacks for network actions.
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.on_move = on_move

    def on_left(self, event) -> None:
        # Input: key event. Output: none.
        # Move cursor left.
        if self.cursor_col > 0:
            self.cursor_col -= 1
            self._draw_board()

    def on_right(self, event) -> None:
        # Input: key event. Output: none.
        # Move cursor right.
        if self.cursor_col < COLS - 1:
            self.cursor_col += 1
            self._draw_board()

    def on_space(self, event) -> None:
        # Input: key event. Output: none.
        # Drop piece in selected column.
        # Prevent space from activating focused widgets (buttons)
        self.send_move(self.cursor_col)
        return "break"

    def send_move(self, column: int) -> None:
        # Input: column (int). Output: none.
        # Send a move request for a specific column.
        # Only allow move on your turn
        if self.over:
            return
        if self.player_id is None:
            return
        if column < 0 or column >= COLS:
            self.log_msg(f"Invalid column: {column + 1}")
            return
        if self.turn != self.player_id:
            self.log_msg("Not your turn")
            return
        try:
            self.log_msg(f"Send move: column={column + 1} (player {self.player_id})")
            # Ask server to place a piece in this column.
            if self.on_move is not None:
                self.on_move(column)
        except OSError:
            self.log_msg("Connection lost")

    def _landing_row(self, column: int) -> Optional[int]:
        # Input: column (int). Output: row index or None.
        # Compute where a piece would land in this column.
        for r in range(ROWS - 1, -1, -1):
            if self.board[r][column] == 0:
                return r
        return None


    def _set_player_panel(self, player_number: int, name: str, image, active: bool) -> None:
        # Input: player_number, name, image, active. Output: none.
        # Update a single player panel UI.
        panel = self.player1_panel if player_number == 1 else self.player2_panel
        name_label = self.player1_name_label if player_number == 1 else self.player2_name_label
        image_label = self.player1_image_label if player_number == 1 else self.player2_image_label
        name_var = self.player1_name_var if player_number == 1 else self.player2_name_var

        name_var.set(name)
        if image is not None and name:
            image_label.config(image=image)
        else:
            image_label.config(image="")

        bg = COLOR_TURN_HIGHLIGHT if active else COLOR_BG
        panel.config(bg=bg)
        name_label.config(bg=bg)
        image_label.config(bg=bg)

    def _reset_player_panels(self) -> None:
        # Input: none. Output: none.
        # Clear player names and images.
        self.player1_base_name = ""
        self.player2_base_name = ""
        self._set_player_panel(1, "", None, False)
        self._set_player_panel(2, "", None, False)

    def _update_turn_highlight(self) -> None:
        # Input: none. Output: none.
        # Highlight the current player's panel.
        both_connected = bool(self.player1_name_var.get()) and bool(self.player2_name_var.get())
        if not both_connected:
            self._set_player_panel(1, self.player1_name_var.get(), self.profile_image_player1, False)
            self._set_player_panel(2, self.player2_name_var.get(), self.profile_image_player2, False)
            return
        active1 = self.turn == 1
        active2 = self.turn == 2
        self._set_player_panel(1, self.player1_name_var.get(), self.profile_image_player1, active1)
        self._set_player_panel(2, self.player2_name_var.get(), self.profile_image_player2, active2)

    def _handle_message(self, message: dict) -> None:
        # Input: message (dict). Output: none.
        # Update UI/game state based on server message.
        """Handle messages coming from the server."""
        # some cases by message type
        mtype = message.get("type")
        if mtype == "welcome":
            self.player_id = message.get("player")
            name = self.name_var.get().strip() or "player"
            self.status_var.set(f"Welcome {name} (Player {self.player_id})")
            self.log_msg(f"Welcome {name}: player {self.player_id}")
            self.canvas.focus_set()
        elif mtype == "state":
            # Update board/turn/winner info from server.
            self.board = message.get("board", self.board)
            self.turn = message.get("turn", self.turn)
            self.over = bool(message.get("game_over"))
            winner = message.get("winner")
            players = message.get("players", {})
            if isinstance(players, dict):
                name1 = players.get("1") or ""
                name2 = players.get("2") or ""
                self.player1_base_name = name1
                self.player2_base_name = name2
                self.player1_name_var.set(name1)
                self.player2_name_var.set(name2)
            self._update_turn_highlight()
            self._draw_board()
            if self.over:
                if winner == 0:
                    self.status_var.set("Draw")
                    self.log_msg("Game over: draw")
                else:
                    self.status_var.set(f"Player {winner} wins")
                    self.log_msg(f"Game over: player {winner} wins")
                # show WIN/LOSE on player panels
                if winner == 1:
                    if self.player1_base_name:
                        self.player1_name_var.set(f"{self.player1_base_name}  WIN")
                    if self.player2_base_name:
                        self.player2_name_var.set(f"{self.player2_base_name}  LOSE")
                elif winner == 2:
                    if self.player2_base_name:
                        self.player2_name_var.set(f"{self.player2_base_name}  WIN")
                    if self.player1_base_name:
                        self.player1_name_var.set(f"{self.player1_base_name}  LOSE")
            else:
                self.status_var.set(f"Turn: Player {self.turn}")
        elif mtype == "error":
            self.log_msg(f"Error: {message.get('message')}")
        elif mtype == "info":
            self.log_msg(f"Info: {message.get('message')}")
        else:
            self.log_msg(str(message))

    def _poll_msgs(self) -> None:
        # Input: none. Output: none.
        # Poll message queue and handle new messages.
        try:
            while True:
                raw = self.msg_queue.get_nowait()
                try:
                    # raw is already a dict from network layer
                    self._handle_message(raw)
                except Exception:
                    self.log_msg(str(raw))
        except queue.Empty:
            pass
        self.root.after(100, self._poll_msgs)


def main() -> None:
    # Input: none. Output: none.
    # Start the GUI app.
    root = tk.Tk()
    app = App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
