# server.py

import socket
import threading
import time
from protocol import encode, decode
from protocol import REGISTER, METRICS, HEARTBEAT, DISCONNECT, ACK, HEARTBEAT_ACK
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/agents":
            with agents_lock:
                data = json.dumps(list(agents.values()))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data.encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # silence HTTP logs

def start_http_server():
    httpd = HTTPServer(("0.0.0.0", 8080), DashboardHandler)
    httpd.serve_forever()

HOST = "0.0.0.0"  # listen on all interfaces
PORT = 9000

# shared state — all connected agents
agents = {}
agents_lock = threading.Lock()

def handle_agent(conn: socket.socket, addr: tuple):
    hostname = None
    print(f"[+] New connection from {addr}")

    try:
        buffer = ""
        while True:
            data = conn.recv(4096).decode("utf-8")
            if not data:
                break

            buffer += data
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if not line.strip():
                    continue

                msg = decode(line)
                msg_type = msg["type"]
                payload = msg["payload"]

                if msg_type == REGISTER:
                    hostname = payload["hostname"]
                    with agents_lock:
                        agents[hostname] = {
                            "addr":       addr[0],
                            "hostname":   hostname,
                            "metrics":    {},
                            "last_seen":  time.time(),
                            "status":     "online"
                        }
                    conn.sendall(encode(ACK, {"message": f"Welcome {hostname}"}))
                    print(f"[+] Agent registered: {hostname} ({addr[0]})")

                elif msg_type == METRICS:
                    with agents_lock:
                        if hostname:
                            agents[hostname]["metrics"] = payload
                            agents[hostname]["last_seen"] = time.time()
                    print(f"[<] {hostname} | CPU {payload.get('cpu')}% | RAM {payload.get('ram')}% | Disk {payload.get('disk')}%")

                elif msg_type == HEARTBEAT:
                    with agents_lock:
                        if hostname:
                            agents[hostname]["last_seen"] = time.time()
                    conn.sendall(encode(HEARTBEAT_ACK))

                elif msg_type == DISCONNECT:
                    print(f"[-] Agent disconnecting: {hostname}")
                    with agents_lock:
                        if hostname:
                            agents[hostname]["status"] = "offline"
                    break

    except (ConnectionResetError, BrokenPipeError):
        print(f"[!] Connection lost: {hostname or addr}")
    finally:
        with agents_lock:
            if hostname and hostname in agents:
                agents[hostname]["status"] = "offline"
        conn.close()
        print(f"[-] Disconnected: {hostname or addr}")

def start():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((HOST, PORT))
        server.listen()
        print(f"[*] NetWatch server listening on {HOST}:{PORT}")
        http_thread = threading.Thread(target=start_http_server, daemon=True)
        http_thread.start()
        print("[*] Dashboard available at http://localhost:8080/api/agents")

        while True:
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_agent, args=(conn, addr), daemon=True)
            thread.start()

if __name__ == "__main__":
    start()