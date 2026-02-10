Updated README.md

# NXBT Joy-Con Bridge (macOS → Ubuntu VM → Nintendo Switch)

This project forwards **right Joy-Con input on macOS** into an **Ubuntu (UTM) VM** which runs **NXBT** to emulate a **Nintendo Switch Pro Controller** over Bluetooth.

It enables:
- simultaneous **stick + button** input (required for Mario Kart)
- a clean separation between:
  - **input capture** (macOS)
  - **controller emulation** (Linux + NXBT)

---

## Architecture

Joy-Con (macOS) → `pygame` → UDP → Ubuntu VM → NXBT → Bluetooth USB dongle → Nintendo Switch

- macOS reads the Joy-Con state and sends UDP packets
- VM receives packets, constructs an NXBT input packet, and streams it at ~120 Hz
- Switch pairs with the NXBT-emulated Pro Controller via **Change Grip / Order**

---

## Requirements

### Hardware
- macOS machine
- Nintendo Switch
- USB Bluetooth dongle passed through to the VM (UTM USB passthrough)
  - CSR8510 works in this setup
- Right Joy-Con (paired to macOS)

### Software
- UTM running Ubuntu Server 22.04 ARM64
- Python 3.10+
- NXBT installed in a venv inside the VM
- pygame installed on macOS

---

## Files

- `joycon_sender.py` (macOS)
  - reads Joy-Con via pygame
  - sends JSON over UDP to the VM
  - includes the **clockwise XYBA rotation mapping** for your two-hand Joy-Con orientation

- `nxbt_receiver.py` (Ubuntu VM)
  - pairs NXBT Pro Controller to Switch
  - receives UDP packets (non-blocking)
  - uses `create_input_packet()` and continuously calls `set_controller_input()` at 120 Hz
  - neutral keepalive when UDP stops (prevents stuck inputs + disconnects)

- `udp_print.py` (Ubuntu VM)
  - debugging tool to print UDP packets

---

## Setup

### 1) VM: create venv + install NXBT
```bash
python3 -m venv ~/venvs/nxbt
source ~/venvs/nxbt/bin/activate
pip install -U pip setuptools wheel
pip install nxbt==0.1.4

2) macOS: install pygame

python3 -m pip install pygame


⸻

Run

1) Start the receiver in the VM (must use venv python as root)

cd ~
sudo -E ~/venvs/nxbt/bin/python3 ~/nxbt_receiver.py

2) Pair on the Switch

On Switch:
	•	Controllers → Change Grip / Order

Wait until the receiver prints state connected.

3) Start the sender on macOS

python3 joycon_sender.py


⸻

Notes / Known gotchas
	•	Always run NXBT using the venv interpreter:
	•	✅ sudo -E ~/venvs/nxbt/bin/python3 …
	•	❌ sudo python3 … (won’t find installed packages)
	•	If you have a local folder named ~/nxbt, it can shadow imports and break NXBT’s multiprocessing. Avoid shadowing.
	•	During development, Change Grip / Order is the reliable way to connect. Reconnect is not guaranteed across dongle resets.

⸻

Next step: behavioural cloning dataset capture

Goal:
	•	Capture (frame, action) pairs:
	•	frame: HDMI capture (video frames)
	•	action: Joy-Con state being sent over UDP
	•	Save as a time-aligned dataset suitable for imitation learning.

---
