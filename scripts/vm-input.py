#!/usr/bin/env python3
"""Stuur muis-/toetsinvoer naar de dev-VM via de QMP-socket.

Vereist dat de VM met een absolute aanwijzer (virtio-tablet) en een QMP-socket
draait (zie Justfile dev-vm-gui). Pixelcoördinaten worden gemapt op het
QEMU-abs-bereik (0..32767) o.b.v. de huidige framebuffer-grootte, uitgelezen
via de PPM-header van een screendump.

Gebruik:
  vm-input.py click X Y [--size WxH]      # linkermuisklik op pixel (X,Y)
  vm-input.py move X Y [--size WxH]
  vm-input.py dblclick X Y [--size WxH]
  vm-input.py key <qcode> [<qcode> ...]   # bv. 'ret' 'esc' 'ctrl-alt-f3'
  vm-input.py type "tekst"                # tikt letterlijke tekst (us-layout)
"""
import json
import os
import socket
import sys
import time

QMP_SOCK = os.environ.get("COOLBX_QMP", "/tmp/coolbx-qmp.sock")
MON_SOCK = os.environ.get("COOLBX_MON", "/tmp/coolbx-mon.sock")
ABS_MAX = 32767


class QmpClient:
    def __init__(self, path):
        self.s = socket.socket(socket.AF_UNIX)
        self.s.connect(path)
        self.f = self.s.makefile("rwb", buffering=0)
        self.f.readline()  # QMP-greeting is precies één regel (geen return)
        self.cmd("qmp_capabilities")

    def _recv(self):
        while True:
            line = self.f.readline()
            if not line:
                raise RuntimeError("QMP-verbinding gesloten")
            msg = json.loads(line)
            if "return" in msg or "error" in msg:
                return msg
            # asynchrone events negeren

    def cmd(self, execute, **args):
        payload = {"execute": execute}
        if args:
            payload["arguments"] = args
        self.f.write((json.dumps(payload) + "\n").encode())
        return self._recv()

    def send_event(self, events):
        return self.cmd("input-send-event", events=events)

    def close(self):
        self.s.close()


def screen_size():
    """Framebuffer-grootte uit de PPM-header van een verse screendump."""
    ppm = "/tmp/coolbx-size.ppm"
    try:
        os.remove(ppm)
    except FileNotFoundError:
        pass
    s = socket.socket(socket.AF_UNIX)
    s.connect(MON_SOCK)
    s.recv(4096)
    s.sendall(b"screendump " + ppm.encode() + b"\n")
    s.close()
    for _ in range(30):
        if os.path.exists(ppm) and os.path.getsize(ppm) > 32:
            break
        time.sleep(0.1)
    with open(ppm, "rb") as fh:
        fh.readline()                      # magic (P6)
        dims = fh.readline().split()       # "W H"
        return int(dims[0]), int(dims[1])


def to_abs(px, py, w, h):
    return int(px / max(w - 1, 1) * ABS_MAX), int(py / max(h - 1, 1) * ABS_MAX)


def abs_event(ax, ay):
    return [
        {"type": "abs", "data": {"axis": "x", "value": ax}},
        {"type": "abs", "data": {"axis": "y", "value": ay}},
    ]


def do_click(q, px, py, w, h, double=False):
    ax, ay = to_abs(px, py, w, h)
    q.send_event(abs_event(ax, ay))
    time.sleep(0.06)
    for _ in range(2 if double else 1):
        q.send_event([{"type": "btn", "data": {"down": True, "button": "left"}}])
        q.send_event([{"type": "btn", "data": {"down": False, "button": "left"}}])
        time.sleep(0.09)


CHARMAP = {c: [c] for c in "abcdefghijklmnopqrstuvwxyz0123456789"}
CHARMAP.update({" ": ["spc"], "/": ["slash"], ".": ["dot"], "-": ["minus"],
                "_": ["shift", "minus"], ":": ["shift", "semicolon"]})


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    cmd, args = sys.argv[1], sys.argv[2:]
    size = None
    if "--size" in args:
        i = args.index("--size")
        size = tuple(int(v) for v in args[i + 1].lower().split("x"))
        del args[i:i + 2]

    if cmd in ("click", "move", "dblclick"):
        px, py = int(args[0]), int(args[1])
        w, h = size or screen_size()
        q = QmpClient(QMP_SOCK)
        if cmd == "move":
            ax, ay = to_abs(px, py, w, h)
            q.send_event(abs_event(ax, ay))
        else:
            do_click(q, px, py, w, h, double=(cmd == "dblclick"))
        q.close()
        print(f"{cmd} @ ({px},{py}) op {w}x{h}")
    elif cmd == "key":
        q = QmpClient(QMP_SOCK)
        for combo in args:
            keys = [{"type": "qcode", "data": k} for k in combo.split("-")]
            q.cmd("send-key", keys=keys)
            time.sleep(0.05)
        q.close()
        print("key:", " ".join(args))
    elif cmd == "type":
        q = QmpClient(QMP_SOCK)
        for ch in args[0]:
            qc = CHARMAP.get(ch)
            if qc:
                q.cmd("send-key", keys=[{"type": "qcode", "data": k} for k in qc])
                time.sleep(0.03)
        q.close()
        print("type:", args[0])
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
