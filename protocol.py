import json

VERSION = "1.0"

# Message types
REGISTER   = "REGISTER"    # agent -> server: introduce yourself
ACK        = "ACK"         # server -> agent: confirmed
METRICS    = "METRICS"     # agent -> server: send stats
ALERT      = "ALERT"       # server -> agent or server internal: threshold crossed
HEARTBEAT  = "HEARTBEAT"   # agent -> server: i'm still alive
HEARTBEAT_ACK = "HEARTBEAT_ACK"  # server -> agent: i see you
DISCONNECT = "DISCONNECT"  # agent -> server: going offline

def encode(msg_type: str, payload: dict = {}) -> bytes:
    message = {
        "version": VERSION,
        "type": msg_type,
        "payload": payload
    }
    return (json.dumps(message) + "\n").encode("utf-8")

def decode(raw: str) -> dict:
    return json.loads(raw.strip())