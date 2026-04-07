# CMPT371 A3 - Connect Four (Networked GUI)

## Student Info
- Name: **Kentaro Yamada (SOLO)**
- Student ID: **301634837**
- Student Email: **kya94@sfu.ca**


## Project Title & Description
This is a simple 2‑player **Connect Four** game using Python sockets. The **server** keeps the board and turn. The **client GUI** sends moves and shows the board. Messages are **JSON Lines** (one JSON per line).

## Architecture
- **Server**: board, turn, win/draw, broadcast state
- **Client (GUI)**: send moves, render board and UI

## Protocol (Simple)
Client → Server:
- `{"type":"join","name":"player"}`
- `{"type":"move","column":3}`

Server → Client:
- `{"type":"welcome","player":1,"rows":6,"cols":7,"win":4}`
- `{"type":"state","board":[...],"turn":1,"winner":null,"game_over":false,"players":{"1":"A","2":"B"}}`

## How to Run (fresh environment)
### Requirements
- Python 3.10+
- No external libraries
- `tkinter` is needed for GUI (usually included with Python on macOS/Windows)

### 1. Check Python
```bash
python --version
```

### 2. Start the server
```bash
python server.py --host 127.0.0.1 --port 6000
```
You will see:
```
[server] listening on 127.0.0.1:6000
```

### 3. Start two clients
Open two terminals (or two computers) and run:
```bash
python client.py
```
Click **Connect** on both windows.

### 4. Wait for opponent
After you click **Connect**, wait for the other player. When both player icons show up, it means the connection is ready.

### 5. Controls
- **Left/Right arrows**: choose column
- **Space**: place piece

## How to Play and Rules
1. Two players connect
2. On your turn, choose a column and press Space to place
3. First to connect 4 wins (or draw if board is full)

## Limitations / Known Issues
- Only 2 players (3rd connection will be rejected)
- Game state is in memory only (server restart resets game)
- If a player disconnects, the game resets

## Files
- `server.py`: game server
- `client.py`: client entry point
- `client_ui.py`: GUI display and UI logic
- `client_network.py`: client networking module
- `requirements.txt`: no external dependencies
- `assets/icon1.png`: player 1 piece image
- `assets/icon2.png`: player 2 piece image
- `assets/p1.png`: player 1 profile image
- `assets/p2.png`: player 2 profile image



## Video Demo Link
- ** ...... **

## AI Reference
This project used AI assistance (Chat GPT) for code reference and wording support.

## Image Credits
Player images were downloaded from a copyright‑free source:
```
https://www.ac-illust.com/main/search_result.php?word=%E7%86%8A
```
