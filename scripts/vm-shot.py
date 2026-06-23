#!/usr/bin/env python3
"""Screenshot van de dev-VM via de QEMU-monitor (HMP screendump) -> PNG.

Robuust voor een autonome agent: verwijdert een eventuele stale PPM, wacht tot het
verse bestand stabiel is, en exit !=0 bij fouten (geen onleesbare traceback, geen
oude screenshot die als 'nieuw' doorgaat).

Gebruik: vm-shot.py [monitor-unix-socket] [output.png]
"""
import os
import socket
import sys
import time

try:
    from PIL import Image
except ImportError:
    print("Pillow ontbreekt (python3-pillow)", file=sys.stderr)
    sys.exit(2)

sock_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/coolbx-mon.sock"
out_png = sys.argv[2] if len(sys.argv) > 2 else "output/shot.png"
ppm = "/tmp/coolbx-shot.ppm"

# Stale PPM weg: anders zouden we bij een mislukte screendump een oude screenshot opslaan.
try:
    os.unlink(ppm)
except FileNotFoundError:
    pass

try:
    s = socket.socket(socket.AF_UNIX)
    s.settimeout(5)
    s.connect(sock_path)
except OSError as e:
    print(f"monitor-socket niet bereikbaar ({sock_path}): {e} — draait de VM?", file=sys.stderr)
    sys.exit(2)

time.sleep(0.3)
try:
    s.recv(65536)  # HMP-banner
except OSError:
    pass
s.sendall(f"screendump {ppm}\n".encode())

# Wacht tot het PPM bestaat én stabiel is (QEMU schrijft async).
last = -1
for _ in range(80):  # ~8s
    time.sleep(0.1)
    try:
        sz = os.path.getsize(ppm)
    except OSError:
        continue
    if sz > 0 and sz == last:
        break
    last = sz
try:
    s.recv(65536)
except OSError:
    pass
s.close()

if not os.path.exists(ppm) or os.path.getsize(ppm) == 0:
    print("screendump leverde geen bestand op", file=sys.stderr)
    sys.exit(3)

img = Image.open(ppm)
img.save(out_png)

# Zwart-scherm-heuristiek zodat 'niets' niet als geslaagde screenshot doorgaat.
gray = img.convert("L")
mean = sum(gray.getdata()) / (gray.width * gray.height)
print(f"{out_png} ({img.width}x{img.height}, gem. luminantie {mean:.1f})")
if mean < 3:
    print("WAARSCHUWING: vrijwel zwart beeld — VM mogelijk nog niet grafisch", file=sys.stderr)
