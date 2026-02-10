import copy
import json
import socket
import time
import nxbt

PORT = 5005
HZ = 120
DEADZONE = 0.08
FAILSAFE_SECONDS = 1.0  # if no UDP for this long, neutralize

def dz(v: float) -> float:
    return 0.0 if abs(v) < DEADZONE else v

def clamp(v: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))

def to_axis(v: float) -> int:
    # NXBT stick range is roughly -100..100
    return int(round(clamp(v) * 100))

def make_packet():
    # Prefer library default if present
    if hasattr(nxbt, "DEFAULT_INPUT_PACKET"):
        return copy.deepcopy(nxbt.DEFAULT_INPUT_PACKET)

    # Fallback packet (works on nxbt 0.1.4 style APIs)
    return {
        nxbt.Sticks.LEFT_STICK:  {"X_VALUE": 0, "Y_VALUE": 0},
        nxbt.Sticks.RIGHT_STICK: {"X_VALUE": 0, "Y_VALUE": 0},
        nxbt.Buttons.A: False, nxbt.Buttons.B: False,
        nxbt.Buttons.X: False, nxbt.Buttons.Y: False,
        nxbt.Buttons.L: False, nxbt.Buttons.R: False,
        nxbt.Buttons.ZL: False, nxbt.Buttons.ZR: False,
        nxbt.Buttons.PLUS: False, nxbt.Buttons.MINUS: False,
        nxbt.Buttons.HOME: False, nxbt.Buttons.CAPTURE: False,
        nxbt.Buttons.L_STICK_PRESS: False, nxbt.Buttons.R_STICK_PRESS: False,
        nxbt.Buttons.DPAD_UP: False, nxbt.Buttons.DPAD_DOWN: False,
        nxbt.Buttons.DPAD_LEFT: False, nxbt.Buttons.DPAD_RIGHT: False,
    }

def neutralize(pkt):
    pkt[nxbt.Sticks.LEFT_STICK]["X_VALUE"] = 0
    pkt[nxbt.Sticks.LEFT_STICK]["Y_VALUE"] = 0
    pkt[nxbt.Buttons.A] = False
    pkt[nxbt.Buttons.B] = False
    pkt[nxbt.Buttons.X] = False
    pkt[nxbt.Buttons.Y] = False

def main():
    print("Starting NXBT...")
    nx = nxbt.Nxbt()

    # Reconnect if NXBT knows prior Switch address(es)
    reconnect = None
    if hasattr(nx, "get_switch_addresses"):
        addrs = nx.get_switch_addresses()
        if isinstance(addrs, (list, tuple)) and len(addrs) > 0:
            reconnect = addrs[0]

    if reconnect:
        print(f"Using reconnect address: {reconnect}")
        idx = nx.create_controller(nxbt.PRO_CONTROLLER, reconnect_address=reconnect)
    else:
        idx = nx.create_controller(nxbt.PRO_CONTROLLER)

    print("Put Switch in: Controllers -> Change Grip/Order")
    nx.wait_for_connection(idx)
    print("Connected. Listening for UDP packets...")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", PORT))
    sock.settimeout(0.25)

    pkt = make_packet()
    last_rx = time.time()

    while True:
        try:
            data, _ = sock.recvfrom(8192)
            msg = json.loads(data.decode("utf-8"))
            last_rx = time.time()

            # Joy-Con axes
            lx = dz(float(msg.get("lx", 0.0)))
            ly = dz(float(msg.get("ly", 0.0)))

            # pygame: up is -1. Switch expects up positive -> invert Y
            pkt[nxbt.Sticks.LEFT_STICK]["X_VALUE"] = to_axis(lx)
            pkt[nxbt.Sticks.LEFT_STICK]["Y_VALUE"] = to_axis(-ly)

            # Buttons
            pkt[nxbt.Buttons.A] = bool(msg.get("a", 0))
            pkt[nxbt.Buttons.B] = bool(msg.get("b", 0))
            pkt[nxbt.Buttons.X] = bool(msg.get("x", 0))
            pkt[nxbt.Buttons.Y] = bool(msg.get("y", 0))

        except TimeoutError:
            # if no packets recently, neutralize so inputs don't stick
            if time.time() - last_rx > FAILSAFE_SECONDS:
                neutralize(pkt)

        # Apply state every tick (supports simultaneous stick + buttons)
        nx.set_controller_input(idx, pkt)
        time.sleep(1.0 / HZ)

if __name__ == "__main__":
    main()
