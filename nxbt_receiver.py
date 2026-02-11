#!/home/andy-ubuntu/venvs/nxbt/bin/python3
"""
nxbt_receiver.py (Ubuntu VM)

Receives UDP JSON packets from macOS (joycon_sender.py) and drives NXBT 0.1.4
as a Nintendo Switch Pro Controller.

Now includes:
- drift  -> Pro Controller R   (packet["R"])
- pause  -> Pro Controller PLUS (packet["PLUS"])
"""

import json
import socket
import time
import nxbt

PORT = 5005
HZ = 120
DEADZONE = 0.08
FAILSAFE_SECONDS = 0.5  # neutralize if no UDP for this long

def dz(v: float) -> float:
    return 0.0 if abs(v) < DEADZONE else v

def clamp(v: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))

def to_axis(v: float) -> int:
    return int(round(clamp(v) * 100))

def neutral(packet: dict) -> None:
    # Clear stick digital flags (present in NXBT's packet schema)
    packet["L_STICK"]["LS_LEFT"] = False
    packet["L_STICK"]["LS_RIGHT"] = False
    packet["L_STICK"]["LS_UP"] = False
    packet["L_STICK"]["LS_DOWN"] = False

    # Neutral analog values
    packet["L_STICK"]["X_VALUE"] = 0
    packet["L_STICK"]["Y_VALUE"] = 0

    # Clear face buttons we use
    packet["A"] = False
    packet["B"] = False
    packet["X"] = False
    packet["Y"] = False

    # Clear drift + pause
    packet["R"] = False
    packet["PLUS"] = False

def main():
    print("Starting NXBT...")
    nx = nxbt.Nxbt(disable_logging=True)

    # Optional reconnect target if NXBT knows prior Switch addresses
    reconnect_target = None
    if hasattr(nx, "get_switch_addresses"):
        addrs = nx.get_switch_addresses()
        if isinstance(addrs, (list, tuple)) and addrs:
            reconnect_target = addrs[0]

    controller_index = nx.create_controller(
        nxbt.PRO_CONTROLLER,
        reconnect_address=reconnect_target
    )

    print("Put Switch in: Controllers -> Change Grip/Order")
    last_state = None
    while True:
        state = nx.state[controller_index]["state"]
        if state != last_state:
            print("NXBT state:", state)
            last_state = state

        if state == "connected":
            break
        if state == "crashed":
            raise RuntimeError(nx.state[controller_index]["errors"])
        time.sleep(0.05)

    # Create a correctly-shaped input packet (NXBT 0.1.4 compatible)
    packet = nx.create_input_packet()

    # UDP socket (non-blocking)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", PORT))
    sock.settimeout(0.0)

    last_rx = time.time()
    latest = {
        "lx": 0.0, "ly": 0.0,
        "a": 0, "b": 0, "x": 0, "y": 0,
        "drift": 0,
        "pause": 0,
        "ts": 0
    }

    print(f"Connected. Receiving UDP on :{PORT} and driving input @ {HZ}Hz")

    while True:
        # Drain queued UDP packets (keep only most recent)
        while True:
            try:
                data, _ = sock.recvfrom(8192)
            except BlockingIOError:
                break
            try:
                latest = json.loads(data.decode("utf-8"))
                last_rx = time.time()
            except Exception:
                pass

        # Failsafe: if sender stops, send neutral packets so Switch stays connected
        if time.time() - last_rx > FAILSAFE_SECONDS:
            neutral(packet)
        else:
            lx = dz(float(latest.get("lx", 0.0)))
            ly = dz(float(latest.get("ly", 0.0)))

            # pygame: up is -1. Convert to Switch convention (up positive)
            packet["L_STICK"]["X_VALUE"] = to_axis(lx)
            packet["L_STICK"]["Y_VALUE"] = to_axis(-ly)

            # Face buttons
            packet["A"] = bool(latest.get("a", 0))
            packet["B"] = bool(latest.get("b", 0))
            packet["X"] = bool(latest.get("x", 0))
            packet["Y"] = bool(latest.get("y", 0))

            # Added buttons
            # drift -> R (Mario Kart default drift)
            packet["R"] = bool(latest.get("drift", 0))

            # pause -> PLUS
            packet["PLUS"] = bool(latest.get("pause", 0))

        # Keepalive: always send packet
        nx.set_controller_input(controller_index, packet)

        # Detect disconnect/crash
        state = nx.state[controller_index]["state"]
        if state != "connected":
            print("NXBT state:", state)
            if state == "crashed":
                raise RuntimeError(nx.state[controller_index]["errors"])

        time.sleep(1.0 / HZ)

if __name__ == "__main__":
    main()
