"""Coolbx OS e2e-harness — host-gedreven VM-client (ADR-0020).

Bundelt de vier interactie-lagen tot één API voor de pytest-tests:
  - laag B: ssh() / ssh_sudo()            — systeemstaat-asserts over SSH
  - laag C: cdp()                          — Chrome DevTools Protocol (via de SSH-tunnel)
  - laag D: screenshot() / find_text() / click() / find_click()  — pixels als laatste redmiddel
  - laag A: wait_for()                     — gepolld predicaat met timeout (NixOS-driver-patroon)

Draait OP DE HOST. Geen gast-software nodig: screendump via de QEMU-monitor, input via QMP+virtio-tablet,
CDP via een SSH local-forward. De CDP-tunnel + kiosk-lifecycle worden door conftest-fixtures beheerd.
"""
import json
import os
import subprocess
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SSH_PORT = "2222"
SSH_USER = "tester"
SSH_PASS = "tester"
SSH_HOST = "127.0.0.1"
MON_SOCK = "/tmp/coolbx-mon.sock"
QMP_SOCK = "/tmp/coolbx-qmp.sock"
CDP_PORT = "9222"

_SSH_BASE = [
    "sshpass", "-p", SSH_PASS, "ssh",
    "-o", "StrictHostKeyChecking=no",
    "-o", "UserKnownHostsFile=/dev/null",
    "-o", "ConnectTimeout=5",
    "-p", SSH_PORT, f"{SSH_USER}@{SSH_HOST}",
]


class CmdError(RuntimeError):
    def __init__(self, cmd, rc, out, err):
        super().__init__(f"rc={rc}: {cmd}\n{err.strip() or out.strip()}")
        self.rc, self.out, self.err = rc, out, err


def _run(argv, stdin=None, timeout=60):
    p = subprocess.run(
        argv, input=stdin, capture_output=True, text=True, timeout=timeout
    )
    return p.returncode, p.stdout, p.stderr


class VM:
    """Eén draaiende dev-VM (vaste socket-/poort-paden uit de Justfile-recepten)."""

    # ---- laag B: SSH / systeemstaat ----
    def ssh(self, cmd, check=True, timeout=60):
        rc, out, err = _run(_SSH_BASE + [cmd], timeout=timeout)
        if check and rc != 0:
            raise CmdError(cmd, rc, out, err)
        return out

    def ssh_ok(self, cmd, timeout=60):
        """True/False i.p.v. exception — handig voor wait_for-predicaten."""
        rc, _, _ = _run(_SSH_BASE + [cmd], timeout=timeout)
        return rc == 0

    def ssh_sudo(self, cmd, check=True, timeout=60):
        wrapped = f"echo {SSH_PASS} | sudo -S sh -c {json.dumps(cmd)}"
        rc, out, err = _run(_SSH_BASE + [wrapped], timeout=timeout)
        if check and rc != 0:
            raise CmdError(cmd, rc, out, err)
        return out

    def reachable(self, timeout=5):
        rc, _, _ = _run(_SSH_BASE + ["true"], timeout=timeout)
        return rc == 0

    # ---- laag C: CDP ----
    def cdp(self, *args, stdin=None, check=True, timeout=30):
        """Roep scripts/vm-cdp.py aan (de SSH-tunnel staat al open via de fixture).
        Geeft geparsede JSON terug indien mogelijk, anders de ruwe tekst. Bij check=False
        valt het terug op stderr als stdout leeg is (diagnostische meldingen staan daar)."""
        argv = ["python3", os.path.join(ROOT, "scripts", "vm-cdp.py"), *args]
        rc, out, err = _run(argv, stdin=stdin, timeout=timeout)
        if check and rc != 0:
            raise CmdError("vm-cdp " + " ".join(args), rc, out, err)
        out = out.strip() or err.strip()
        try:
            return json.loads(out)
        except (json.JSONDecodeError, ValueError):
            return out

    def cdp_eval(self, js, **kw):
        return self.cdp("eval", "-", stdin=js, **kw)

    def cdp_fill(self, selector, value, **kw):
        """Vul een webformulier-veld (React/Vue-proof). Geeft {ok, value} of {ok:false,err}."""
        return self.cdp("fill", selector, value, **kw)

    def cdp_type(self, text, **kw):
        """Typ in het gefocuste element via CDP Input.insertText."""
        return self.cdp("type", text, **kw)

    def cdp_page_count(self):
        # Tel ENKEL targets van type 'page' (niet 'background_page' van ingebouwde extensies).
        # Regelformaat: '[          page] <url>' → het type staat tussen [ ] vóór de '] '.
        rc, out, _ = _run(
            ["python3", os.path.join(ROOT, "scripts", "vm-cdp.py"), "targets"]
        )
        if rc != 0:
            return 0
        return sum(
            1 for ln in out.splitlines()
            if ln.split("]")[0].strip(" [") == "page"
        )

    def focus_contract(self):
        """Lees de Focus-integratiecontract-status uit chrome://policy (robuust; omzeilt de
        flaky MV3-SW). Geeft de toegepaste 3rdparty-managed-waarden + ExtensionSettings-status."""
        pols = self.cdp("policy")
        if not isinstance(pols, list):
            return {}
        by = {p.get("name"): p for p in pols}
        return {
            "server_url": by.get("serverUrl", {}).get("value"),
            "kiosk_mode": by.get("kioskMode", {}).get("value"),
            "managed_status": by.get("serverUrl", {}).get("status"),
            "ext_settings": "ExtensionSettings" in by,
            "ext_settings_status": by.get("ExtensionSettings", {}).get("status"),
        }

    def cdp_up(self):
        rc, _, _ = _run(
            ["python3", os.path.join(ROOT, "scripts", "vm-cdp.py"), "targets"],
            timeout=10,
        )
        return rc == 0

    # ---- kiosk-lifecycle ----
    def kiosk_stop(self):
        # VOLGORDE telt: dood eerst de while-loop (chromium-kiosk.sh), anders herstart die
        # chromium — met de óúde sessie-env (incl. een eventuele debug-flag). Pas daarna sway/chromium.
        self.ssh_sudo(
            "systemctl stop coolbx-kiosk 2>/dev/null; systemctl reset-failed coolbx-kiosk 2>/dev/null; "
            "pkill -9 -f chromium-kiosk.sh 2>/dev/null; pkill -9 sway 2>/dev/null; "
            "pkill -9 -f -- '--app=' 2>/dev/null; pkill -9 chromium 2>/dev/null; "
            "umount -l /var/lib/coolbx-kiosk 2>/dev/null; coolbx-vt-lock unlock 2>/dev/null; true",
            check=False,
        )

    def kiosk_start(self, url="file:///usr/share/coolbx/kiosk/placeholder.html", debug=True):
        env = f"COOLBX_KIOSK_URL={url}"
        if debug:
            env = "COOLBX_KIOSK_DEBUG=1 " + env
        # setsid + nohup: de start-helper blokkeert (sway-sessie); we willen 'm gedetacht.
        self.ssh_sudo(
            f"setsid sh -c 'env {env} /usr/bin/coolbx-kiosk-start' >/dev/null 2>&1 &",
            check=False,
        )

    def kiosk_active(self):
        return self.ssh_ok("echo tester | sudo -S systemctl is-active --quiet coolbx-kiosk")

    def chromium_running(self):
        # comm is afgekapt op 15 tekens ('chromium-browse') → pgrep op substring 'chromium'.
        return self.ssh_ok("pgrep chromium >/dev/null 2>&1")

    # ---- laag D: pixels (screendump + QMP-input + OCR) ----
    def screenshot(self, path):
        _run(["python3", os.path.join(ROOT, "scripts", "vm-shot.py"), MON_SOCK, path])
        return path

    def click(self, x, y):
        _run(["python3", os.path.join(ROOT, "scripts", "vm-input.py"), "click", str(x), str(y)])

    def attest_sign(self, challenge, as_user=None):
        """Vraag de attest-daemon (coolbx-attestd) om een challenge te tekenen, via de unix-socket.
        Geeft {deviceId, session, signature} of {error}. Met as_user=<user> verbindt de client als
        die user (sudo -u) — zo test je de peer-cred session-claim (coolbx-kiosk → session=kiosk)."""
        py = (
            "import socket,json,sys;"
            "s=socket.socket(socket.AF_UNIX);s.settimeout(5);s.connect('/run/coolbx-attest.sock');"
            "s.sendall(json.dumps({'challenge':sys.argv[1]}).encode()+b'\\n');"
            "sys.stdout.write(s.recv(4096).decode())"
        )
        client = f"python3 -c {json.dumps(py)} {json.dumps(challenge)}"
        if as_user:
            cmd = f"echo {SSH_PASS} | sudo -S -u {as_user} {client}"
        else:
            cmd = client
        out = _run(_SSH_BASE + [cmd])[1]
        try:
            return json.loads(out.strip().splitlines()[-1]) if out.strip() else {"error": "leeg"}
        except (json.JSONDecodeError, ValueError, IndexError):
            return {"error": out.strip()}

    def type_text(self, text):
        """QMP-toetsenbord (host): typt in wat focus heeft — werkt op GNOME én sway, native velden."""
        _run(["python3", os.path.join(ROOT, "scripts", "vm-input.py"), "type", text])

    def key(self, *keys):
        """QMP-toetsaanslagen, bv. key('ret') of key('ctrl-a')."""
        _run(["python3", os.path.join(ROOT, "scripts", "vm-input.py"), "key", *keys])

    def find_text(self, text, path="/tmp/coolbx-ocr.png"):
        """OCR-locate: screendump -> tesseract -> (x,y)-midden van de tekst, of None."""
        self.screenshot(path)
        rc, out, _ = _run(
            ["python3", os.path.join(ROOT, "scripts", "vm-ocr.py"), "find", path, text]
        )
        if rc != 0 or not out.strip():
            return None
        try:
            d = json.loads(out)
            return (d["x"], d["y"])
        except (json.JSONDecodeError, KeyError):
            return None

    def find_click(self, text):
        pos = self.find_text(text)
        if pos:
            self.click(*pos)
        return pos


# ---- laag A: orkestratie ----
def wait_for(pred, timeout=60, interval=1.0, desc="conditie"):
    """Poll pred() tot truthy of timeout. Geeft de laatste truthy-waarde terug; raise bij timeout."""
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        try:
            last = pred()
            if last:
                return last
        except Exception:
            last = None
        time.sleep(interval)
    raise TimeoutError(f"timeout na {timeout}s op: {desc}")
