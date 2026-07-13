"""VT-lockdown / kiosk-escape (ADR-0016, Focus-audit F-06-009).

De kiosk draait op VT3 met VT-switching op kernelniveau geblokkeerd
(VT_LOCKSWITCH via coolbx-vt-lock, gezet door coolbx-kiosk-start). Dit
codificeert het tot nu toe alleen handmatig bewezen gedrag uit ADR-0016:

  1. Ctrl+Alt+F2/F4 (QMP send-key, dus een échte toetsaanslag op de virtuele
     console) verandert de actieve VT niet zolang de kiosk draait; ook een
     root-`chvt` doet dat niet.
  2. Na kiosk-stop ontgrendelt ExecStopPost (coolbx-kiosk-return) en keert
     het systeem naar VT2 terug; daarna werkt VT-switchen weer — óók via de
     toetsencombinatie. Die laatste stap is meteen de controle dat de
     send-key-route werkt (anders zou test 1 vacuous kunnen slagen).
"""
import time

from harness import wait_for


def _active_vt(vm):
    """Actieve VT zonder controlling-tty-vereiste (fgconsole werkt niet over SSH)."""
    return vm.ssh("cat /sys/class/tty/tty0/active").strip()


def test_vt_switch_geblokkeerd_in_kiosk(kiosk):
    vm = kiosk
    wait_for(lambda: _active_vt(vm) == "tty3", timeout=30, interval=1, desc="kiosk op VT3")

    # Echte toetsaanslagen: kernel/compositor mogen de switch niet uitvoeren.
    for combo in ("ctrl-alt-f2", "ctrl-alt-f4", "ctrl-alt-f1"):
        vm.key(combo)
        time.sleep(1.5)
        assert _active_vt(vm) == "tty3", f"VT-switch via {combo} ontsnapte uit de kiosk"

    # Ook een expliciete root-switch mag niet door de kernel-lock heen.
    # (Met VT_LOCKSWITCH actief kan chvt hangen op VT_WAITACTIVE → timeout.)
    vm.ssh_sudo("timeout 3 chvt 2; true", check=False)
    time.sleep(1)
    assert _active_vt(vm) == "tty3", "root-chvt ontsnapte uit de vergrendelde kiosk-VT"


def test_vt_unlock_na_kiosk_stop(kiosk):
    vm = kiosk
    wait_for(lambda: _active_vt(vm) == "tty3", timeout=30, interval=1, desc="kiosk op VT3")

    # Stop de kiosk: ExecStopPost = coolbx-kiosk-return → unlock + terug naar VT2.
    # (Dit bewijst meteen dat de unlock werkt: de return-chvt slaagt alleen ontgrendeld.)
    vm.kiosk_stop()
    wait_for(lambda: _active_vt(vm) != "tty3", timeout=20, interval=1, desc="kiosk-return verlaat VT3")

    # Controle op de send-key-route (maakt test 1 niet-vacuous): ontgrendeld
    # moet dezelfde toetsencombinatie WÉL switchen.
    vm.key("ctrl-alt-f3")
    wait_for(lambda: _active_vt(vm) == "tty3", timeout=10, interval=1, desc="VT-switch werkt weer na unlock")

    # Netjes terug naar de GNOME-VT.
    vm.ssh_sudo("chvt 2", check=False)
