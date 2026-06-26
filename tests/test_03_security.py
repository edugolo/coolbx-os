"""Veiligheidsregressie — de CDP-debugpoort is DEV-ONLY (ADR-0020).

Een open remote-debugging-port in een productie-toetskiosk = volledige browsercontrole
(valsspeel-vector). Twee complementaire checks:
  1. statisch: de gebakken kiosk-launch zet de debugpoort ENKEL achter COOLBX_KIOSK_DEBUG;
  2. dynamisch (autoritatief): een non-debug kiosk LUISTERT niet op poort 9222.

Draait als laatste en beheert z'n eigen kiosk-lifecycle (gebruikt de `kiosk`-fixture NIET).
"""
import time

from harness import wait_for


def test_debug_port_is_behind_env_gate(vm):
    """Statische garantie: de flag staat binnen de COOLBX_KIOSK_DEBUG-gate, niet onvoorwaardelijk."""
    src = vm.ssh("cat /usr/share/coolbx/kiosk/chromium-kiosk.sh")
    assert "remote-debugging-port=9222" in src, "debug-flag ontbreekt volledig?"
    assert 'COOLBX_KIOSK_DEBUG:-0}" = "1"' in src, "debug-flag zit niet achter de env-gate"
    # de poort-regel mag niet buiten het if-blok staan: check dat 'remote-debugging-port'
    # na de gate-conditie komt (simpele volgorde-heuristiek).
    assert src.index("COOLBX_KIOSK_DEBUG") < src.index("remote-debugging-port=9222")


def test_nondebug_kiosk_has_no_open_cdp_port(vm):
    vm.kiosk_stop()
    wait_for(lambda: not vm.chromium_running(), timeout=25, interval=2, desc="chromium gestopt")

    vm.kiosk_start(debug=False)
    wait_for(vm.kiosk_active, timeout=40, interval=2, desc="coolbx-kiosk active (non-debug)")
    wait_for(vm.chromium_running, timeout=40, interval=2, desc="non-debug chromium up")
    time.sleep(5)  # Chromium volledig laten opstarten vóór de poort-check

    # AUTORITATIEF: luistert er iets op 9222? (de flag-substring in child-cmdlines is onbetrouwbaar)
    port = vm.ssh_sudo(
        "ss -ltn 2>/dev/null | grep -q ':9222' && echo OPEN || echo DICHT", check=False
    )
    vm.kiosk_stop()
    assert "DICHT" in port, "CDP-poort 9222 staat OPEN in een non-debug kiosk (prod-lek!)"
