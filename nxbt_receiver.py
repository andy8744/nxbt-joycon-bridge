# changed to connect like tui.py
import json
import socket
import time
import nxbt

PORT = 5005
HZ = 120
DEADZONE = 0.08
FAILSAFE_SECONDS = 0.5  # if no UDP for this long -> neutral

def dz(v: float) -> float:
    return 0.0 if abs(v) < DEADZONE else v

def clamp(v: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))

def to_axis(v: float) -> int:
    return int(round(clamp(v) * 100))

def neutral(packet):
    # Reset stick direction flags and values
    packet["L_STICK"]["LS_LEFT"] = False
    packet["L_STICK"]["LS_RIGHT"] = False
    packet["L_STICK"]["LS_UP"] = False
    packet["L_STICK"]["LS_DOWN"] = False
    packet["L_STICK"]["X_VALUE"] = 0
    packet["L_STICK"]["Y_VALUE"] = 0

    # Reset buttons we use
    packet["A"] = False
    packet["B"] = False
    packet["X"] = False
    packet["Y"] = False

def main():
    print("Starting NXBT...")
    nx = nxbt.Nxbt(disable_logging=True)

    # Reconnect target if NXBT knows prior Switch addresses
    reconnect_target = None
    if hasattr(nx, "get_switch_addresses"):
        addrs = nx.get_switch_addresses()
        if isinstance(addrs, (list, tuple)) and addrs:
            reconnect_target = addrs[0]

    controller_index = nx.create_controller(
        nxbt.PRO_CONTROLLER,
        reconnect_address=reconnect_target
    )

    last_state = None
    print("Put Switch in: Controllers -> Change Grip/Order")
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

    # IMPORTANT: build packet via NXBT, like the TUI does
    packet = nx.create_input_packet()

    # UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", PORT))
    sock.settimeout(0.0)  # non-blocking

    last_rx = time.time()
    latest = {"lx": 0.0, "ly": 0.0, "a": 0, "b": 0, "x": 0, "y": 0}

    print(f"Connected. Receiving UDP on :{PORT} and driving input @ {HZ}Hz")

    while True:
        # Drain any pending UDP packets (keep only latest)
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

        # If UDP stopped, neutralise so nothing sticks and Switch sees valid idle reports
        if time.time() - last_rx > FAILSAFE_SECONDS:
            neutral(packet)
        else:
            lx = dz(float(latest.get("lx", 0.0)))
            ly = dz(float(latest.get("ly", 0.0)))

            # pygame: up is -1. Convert to Switch convention (up positive)
            x = to_axis(lx)
            y = to_axis(-ly)

            # Set direct axis values (this is what TUI input_worker computes)
            packet["L_STICK"]["X_VALUE"] = x
            packet["L_STICK"]["Y_VALUE"] = y

            # Set buttons
            packet["A"] = bool(latest.get("a", 0))
            packet["B"] = bool(latest.get("b", 0))
            packet["X"] = bool(latest.get("x", 0))
            packet["Y"] = bool(latest.get("y", 0))

        # Keepalive: always send a packet at 120 Hz
        nx.set_controller_input(controller_index, packet)

        # Watch for disconnect/crash
        state = nx.state[controller_index]["state"]
        if state != "connected":
            print("NXBT state:", state)
            if state == "crashed":
                raise RuntimeError(nx.state[controller_index]["errors"])
            # If it’s reconnecting, just keep looping; Change Grip/Order may be needed again.

        time.sleep(1.0 / HZ)

if __name__ == "__main__":
    main()
