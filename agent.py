# agent.py
import socket
import pynvml
import time
import threading
import psutil
import platform
from protocol import encode, decode, REGISTER, METRICS, HEARTBEAT, DISCONNECT

SERVER_IP = "127.0.0.1"  # change to actual server IP
SERVER_PORT = 9000
METRICS_INTERVAL = 3    # seconds
HEARTBEAT_INTERVAL = 10 # seconds

def collect_gpu_metrics() -> dict:
    try:
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        util   = pynvml.nvmlDeviceGetUtilizationRates(handle)
        mem    = pynvml.nvmlDeviceGetMemoryInfo(handle)
        temp   = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
        return {
            "gpu_util":         util.gpu,
            "gpu_mem_used_mb":  round(mem.used  / 1024 / 1024, 1),
            "gpu_mem_total_mb": round(mem.total / 1024 / 1024, 1),
            "gpu_temp":         temp
        }
    except Exception:
        return {}  # machine has no GPU, just skip

def collect_metrics() -> dict:
    net = psutil.net_io_counters()
    data = {
        "CPU":          round(psutil.cpu_percent(interval=1), 1),
        "RAM":          round(psutil.virtual_memory().percent, 1),
        "DISK":         round(psutil.disk_usage("/").percent, 1),
        "net_sent_mb":  round(net.bytes_sent / 1024 / 1024, 2),
        "net_recv_mb":  round(net.bytes_recv / 1024 / 1024, 2),
        "uptime":       int(time.time() - psutil.boot_time())
    }
    data.update(collect_gpu_metrics())
    return data

def send_heartbeat(sock: socket.socket, stop_event: threading.Event):
    while not stop_event.is_set():
        time.sleep(HEARTBEAT_INTERVAL)
        try:
            sock.sendall(encode(HEARTBEAT))
        except:
            break

def run():
    hostname = platform.node()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.connect((SERVER_IP, SERVER_PORT))
        print(f"[+] Connected to server at {SERVER_IP}:{SERVER_PORT}")

        # register
        sock.sendall(encode(REGISTER, {"hostname": hostname}))
        response = decode(sock.recv(1024).decode("utf-8"))
        print(f"[+] Server: {response['type']} — {response['payload']}")

        # heartbeat thread
        stop_event = threading.Event()
        hb_thread = threading.Thread(target=send_heartbeat, args=(sock, stop_event), daemon=True)
        hb_thread.start()

        # metrics loop
        try:
            while True:
                metrics = collect_metrics()
                sock.sendall(encode(METRICS, metrics))
                print(f"[>] Sent metrics: CPU {metrics['CPU']}% | RAM {metrics['RAM']}% | Disk {metrics['DISK']}%")
                time.sleep(METRICS_INTERVAL)
        except KeyboardInterrupt:
            print("\n[!] Shutting down agent...")
            sock.sendall(encode(DISCONNECT, {"hostname": hostname}))
        finally:
            stop_event.set()

if __name__ == "__main__":
    run()