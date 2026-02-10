# NXBT Joy-Con Bridge

Mac → Python → UDP → NXBT → Nintendo Switch

- macOS reads a right Joy-Con via pygame
- Sends controller state over UDP
- Ubuntu VM receives packets
- NXBT emulates a Pro Controller

Status:
- UDP transport verified
- NXBT controller creation works
- Next: integrate UDP → NXBT input loop
