#!/usr/bin/env python3
"""Connect Four TCP server (2-player). JSON Lines protocol.
- The server owns the game state (board, turn, winner)
- Each client sends JSON messages (one per line)
- The server broadcasts updated state after each move
"""

import argparse
import json
import socket
import threading
from typing import Dict, List, Optional


ROWS = 6
COLS = 7
WIN = 4


def send_json_line(connection: socket.socket, obj: dict) -> None:
    # Input: connection (socket), obj (dict). Output: None.
    # Send one JSON object followed by newline to the socket.
    data = json.dumps(obj, ensure_ascii=True) + "\n"
    connection.sendall(data.encode("utf-8"))




class GameState:
    def __init__(self) -> None:
        # Input: none. Output: none.
        # Initialize empty game state.
        # shared game data (protected by lock)
        self.lock = threading.RLock()
        self.board = [[0 for _ in range(COLS)] for _ in range(ROWS)]  # 0 empty, 1 P1, 2 P2
        self.turn = 1  # player id (1 or 2)
        self.winner: Optional[int] = None
        self.game_over = False
        # player sockets + display names
        self.players: Dict[int, socket.socket] = {}
        self.names: Dict[int, str] = {}

    def reset(self) -> None:
        # Input: none. Output: none.
        # Reset board and game status.
        self.board = [[0 for _ in range(COLS)] for _ in range(ROWS)]
        self.turn = 1
        self.winner = None
        self.game_over = False

    def available_row(self, column: int) -> Optional[int]:
        # Input: column (int). Output: row index or None.
        # Find lowest empty row in a column.
        """Return the lowest empty row for a column, or None if full."""
        for r in range(ROWS - 1, -1, -1):
            if self.board[r][column] == 0:
                return r
        return None

    def check_win(self, r: int, c: int, player: int) -> bool:
        # Input: r, c, player. Output: True if 4-in-a-row, else False.
        # Check win condition from a placed piece.
        """Check 4-in-a-row from the last placed piece."""
        # We only need to search lines that pass through the last move (r, c),
        # because any new win must include the newest piece.
        #
        # We check 4 directions:
        # 1 Horizontal:
        # 2 Vertical
        # 3 Diagonal
        # 4 Diagonal
        #
        # For each direction, count consecutive pieces of the same player
        #       forward and backward, then add 1 for the current piece.
        def count(dr: int, dc: int) -> int:
            # Input: direction (dr, dc). Output: number of same-colored pieces.
            # Walk step-by-step in one direction until we hit board edge or other piece.
            rr, cc, n = r + dr, c + dc, 0
            while 0 <= rr < ROWS and 0 <= cc < COLS and self.board[rr][cc] == player:
                n += 1
                rr += dr
                cc += dc
            return n

        for dr, dc in [(0, 1), (1, 0), (1, 1), (1, -1)]:
            # total = pieces in positive direction + pieces in negative direction + current piece
            total = 1 + count(dr, dc) + count(-dr, -dc)
            if total >= WIN:
                return True
        return False

    def is_full(self) -> bool:
        # Input: none. Output: True if board full, else False.
        # Check if the board is full (top row has no empty cells).
        """Board is full if the top row has no empty cells."""
        return all(self.board[0][c] != 0 for c in range(COLS))


class Server:
    def __init__(self, host: str, port: int) -> None:
        # Input: host (str), port (int). Output: none.
        # Initialize server and shared state.
        self.host = host
        self.port = port
        # shared game state
        self.game = GameState()
        # list of connected sockets (for broadcast)
        self.conns: List[socket.socket] = []
        self.conn_lock = threading.Lock()

    def broadcast(self, obj: dict) -> None:
        # Input: obj (dict). Output: none.
        # Send a message to all connected clients.
        data = json.dumps(obj, ensure_ascii=True) + "\n"
        with self.conn_lock:
            dead = []
            for connection in self.conns:
                try:
                    connection.sendall(data.encode("utf-8"))
                except OSError:
                    dead.append(connection)
            for d in dead:
                if d in self.conns:
                    self.conns.remove(d)

    def assign_player(self, connection: socket.socket, name: str) -> Optional[int]:
        # Input: connection (socket), name (str). Output: player id or None.
        # Assign player 1 or 2, or reject if full.
        with self.game.lock:
            if 1 not in self.game.players:
                self.game.players[1] = connection
                self.game.names[1] = name
                return 1
            if 2 not in self.game.players:
                self.game.players[2] = connection
                self.game.names[2] = name
                return 2
            return None

    def remove_player(self, connection: socket.socket) -> None:
        # Input: connection (socket). Output: none.
        # Remove player and reset game if someone leaves.
        with self.game.lock:
            remove_id = None
            for player_id, c in self.game.players.items():
                if c is connection:
                    remove_id = player_id
                    break
            if remove_id is not None:
                del self.game.players[remove_id]
                if remove_id in self.game.names:
                    del self.game.names[remove_id]
                self.game.reset()
                self.broadcast({"type": "info", "message": "player_left_reset"})
                self.broadcast_state()

    def broadcast_state(self) -> None:
        # Input: none. Output: none.
        # Broadcast current game state to all clients.
        with self.game.lock:
            state = self._state_dict()
            self.broadcast(state)
            print("[server] broadcast state")

    def _state_dict(self) -> dict:
        # Input: none. Output: dict.
        # Build a state message dictionary.
        return {
            "type": "state",
            "board": self.game.board,
            "turn": self.game.turn,
            "winner": self.game.winner,
            "game_over": self.game.game_over,
            "players": self.game.names,
        }

    def handle_move(self, player: int, column: int) -> dict:
        # Input: player id, column. Output: response dict.
        # Validate and apply a move, then broadcast state.
        # One move updates board, checks win, then sends new state
        with self.game.lock:
            # validate move
            err = self._validate_move(player, column)
            if err is not None:
                return err
            # place piece
            row = self.game.available_row(column)
            self.game.board[row][column] = player
            # check win / draw / next turn
            self._after_move(row, column, player)
            # send updated board to all
            self.broadcast_state()
            return {"type": "ok"}

    def _validate_move(self, player: int, column: int) -> Optional[dict]:
        # Input: player id, column. Output: error dict or None.
        # Check if a move is allowed.
        if self.game.game_over:
            return {"type": "error", "message": "game_over"}
        if player != self.game.turn:
            return {"type": "error", "message": "not_your_turn"}
        if not (0 <= column < COLS):
            return {"type": "error", "message": "invalid_col"}
        if self.game.available_row(column) is None:
            return {"type": "error", "message": "column_full"}
        return None

    def _after_move(self, row: int, column: int, player: int) -> None:
        # Input: row, column, player. Output: none.
        # Update winner/turn after a valid move.
        if self.game.check_win(row, column, player):
            self.game.game_over = True
            self.game.winner = player
            return
        if self.game.is_full():
            self.game.game_over = True
            self.game.winner = 0
            return
        # next player's turn
        self.game.turn = 2 if self.game.turn == 1 else 1

    def handle_client(self, connection: socket.socket, addr) -> None:
        # Input: connection (socket), addr (client address). Output: none.
        # Read client messages in a loop and respond.
        with connection:
            print(f"[server] connection from {addr}")
            f = connection.makefile("r", encoding="utf-8", newline="\n")
            player_id: Optional[int] = None
            for line in f:
                # Each line should be one JSON message.
                line = line.strip()
                if not line:
                    continue
                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    send_json_line(connection, {"type": "error", "message": "invalid_json"})
                    continue

                mtype = message.get("type")
                if mtype == "join":
                    player_id = self._handle_join(connection, message)
                elif mtype == "move":
                    self._handle_move_msg(connection, player_id, message)
                elif mtype == "quit":
                    # Client requested disconnect.
                    break
                else:
                    send_json_line(connection, {"type": "error", "message": "unknown_type"})

        if player_id is not None:
            self.remove_player(connection)
        print(f"[server] disconnected {addr}")

    def _handle_join(self, connection: socket.socket, message: dict) -> Optional[int]:
        # Input: connection (socket), message (dict). Output: player id or None.
        # Process join request.
        name = message.get("name", "player")
        player_id = self.assign_player(connection, name)
        if player_id is None:
            send_json_line(connection, {"type": "error", "message": "room_full"})
            return None
        print(f"[server] join: player {player_id} ({name})")
        # Send welcome info (player id + board size).
        send_json_line(
            connection,
            {
                "type": "welcome",
                "player": player_id,
                "rows": ROWS,
                "cols": COLS,
                "win": WIN,
            },
        )
        # Share the current state with all clients.
        self.broadcast_state()
        return player_id

    def _handle_move_msg(self, connection: socket.socket, player_id: Optional[int], message: dict) -> None:
        # Input: connection (socket), player_id, message (dict). Output: none.
        # Process move request.
        # Validate that sender is a joined player, then apply move
        if player_id is None:
            send_json_line(connection, {"type": "error", "message": "not_joined"})
            return
        column = message.get("column")
        if not isinstance(column, int):
            send_json_line(connection, {"type": "error", "message": "col_required"})
            return
        print(f"[server] move from player {player_id}: column={column}")
        resp = self.handle_move(player_id, column)
        if resp.get("type") == "error":
            print(f"[server] move error: {resp.get('message')}")
        send_json_line(connection, resp)
        # Send state directly to mover as well (extra safety)
        if resp.get("type") == "ok":
            send_json_line(connection, self._state_dict())

    def serve(self) -> None:
        # Input: none. Output: none.
        # Start listening and accept clients forever.
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.host, self.port))
            s.listen()
            print(f"[server] listening on {self.host}:{self.port}")
            while True:
                connection, addr = s.accept()
                with self.conn_lock:
                    self.conns.append(connection)
                t = threading.Thread(target=self.handle_client, args=(connection, addr), daemon=True)
                t.start()


def main() -> None:
    # Input: none. Output: none.
    # Parse args and start server.
    parser = argparse.ArgumentParser(description="Connect Four Server (TCP)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=6000)
    args = parser.parse_args()
    try:
        Server(args.host, args.port).serve()
    except KeyboardInterrupt:
        print("[server] terminal killed")


if __name__ == "__main__":
    main()
