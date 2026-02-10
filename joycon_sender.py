import json
import socket
import time
import pygame

VM_IP = "192.168.64.2"
PORT = 5005
HZ = 120
DEADZONE = 0.08

def dz(v: float) -> float:
    return 0.0 if abs(v) < DEADZONE else v

def clamp(v: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))

def main():
    pygame.init()
    pygame.joystick.init()

    if pygame.joystick.get_count() == 0:
        raise SystemExit("No joystick detected. Pair/connect the Joy-Con first.")

    js = pygame.joystick.Joystick(0)
    js.init()

    print("Using:", js.get_name())
    print(f"Streaming UDP to {VM_IP}:{PORT} @ {HZ}Hz")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    while True:
        pygame.event.pump()

        # Your mapping
        lx = dz(js.get_axis(0))             # left/right
        ly = dz(js.get_axis(1))             # up/down (up=-1)
        a  = js.get_button(1)               # A
        b  = js.get_button(3)               # B
        x  = js.get_button(0)               # X
        y  = js.get_button(2)               # Y

        pkt = {
            "lx": clamp(lx),
            "ly": clamp(ly),
            "a": int(a),
            "b": int(b),
            "x": int(x),
            "y": int(y),
            "ts": time.time(),
        }
        sock.sendto(json.dumps(pkt).encode("utf-8"), (VM_IP, PORT))
        time.sleep(1.0 / HZ)

if __name__ == "__main__":
    main()
