#!/usr/bin/env python3
"""Maak een screenshot van de dev-VM via de QEMU-monitor (HMP screendump) en
converteer naar PNG. Zo kan een autonome agent de grafische sessie 'bekijken'.

Gebruik: vm-shot.py <monitor-unix-socket> <output.png>
"""
import socket
import sys
import time
from PIL import Image

sock_path = sys.argv[1]
out_png = sys.argv[2]
ppm = "/tmp/coolbx-shot.ppm"

s = socket.socket(socket.AF_UNIX)
s.connect(sock_path)
time.sleep(0.3)
try:
    s.recv(65536)  # HMP-banner
except OSError:
    pass
s.sendall(f"screendump {ppm}\n".encode())
time.sleep(1.2)
try:
    s.recv(65536)
except OSError:
    pass
s.close()

Image.open(ppm).save(out_png)
print(out_png)
