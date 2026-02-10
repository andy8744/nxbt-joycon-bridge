import json
import socket
import time

PORT = 5005

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", PORT))
    sock.settimeout(1.0)

    print(f"Listening on UDP 0.0.0.0:{PORT} ... Ctrl+C to stop")

    last = time.time()
    count = 0

    while True:
        try:
            data, addr = sock.recvfrom(8192)
        except TimeoutError:
            print("(timeout) no packet in last 1s")
            continue

        count += 1
        now = time.time()
        dt = now - last
        last = now

        raw = data.decode("utf-8", errors="replace")
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            msg = raw

        print(f"[{count}] from {addr} dt={dt:.3f}s -> {msg}")

if __name__ == "__main__":
    main()
