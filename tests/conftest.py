"""pytest-fixtures voor de Coolbx OS e2e-harness (ADR-0020).

Beheert de VM-bereikbaarheid, de CDP-SSH-tunnel (session-scoped, ControlMaster) en de
kiosk-lifecycle. Vereist een draaiende dev-VM (`just dev-vm` of `dev-vm-gui`); `just e2e`
zorgt dat die er is.
"""
import subprocess
import time

import pytest

from harness import VM, wait_for, _SSH_BASE, CDP_PORT, SSH_PORT, SSH_PASS, SSH_USER, SSH_HOST

_CTL = "/tmp/coolbx-e2e-cdp.sock"


@pytest.fixture(scope="session")
def vm():
    v = VM()
    if not wait_for(v.reachable, timeout=180, interval=2, desc="VM-SSH bereikbaar"):
        pytest.fail("VM niet bereikbaar op :2222 — start 'just dev-vm' eerst")
    return v


@pytest.fixture(scope="session")
def cdp_tunnel():
    """Eén persistente SSH local-forward (-L 9222) voor de hele sessie via ControlMaster."""
    subprocess.run(
        ["sshpass", "-p", SSH_PASS, "ssh", "-MNfT", "-S", _CTL,
         "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
         "-o", "ExitOnForwardFailure=yes",
         "-L", f"{CDP_PORT}:localhost:{CDP_PORT}", "-p", SSH_PORT, f"{SSH_USER}@{SSH_HOST}"],
        check=False, capture_output=True, text=True,
    )
    yield
    subprocess.run(
        ["sshpass", "-p", SSH_PASS, "ssh", "-S", _CTL, "-O", "exit",
         "-p", SSH_PORT, f"{SSH_USER}@{SSH_HOST}"],
        check=False, capture_output=True, text=True,
    )


@pytest.fixture(scope="module")
def kiosk(vm, cdp_tunnel):
    """Start de debug-kiosk (CDP-poort aan), wacht tot een page-target leeft, en ruim op.
    Module-scoped: breekt af vóór de security-test (eigen non-debug-lifecycle) draait."""
    vm.kiosk_stop()
    time.sleep(2)
    vm.kiosk_start(debug=True)
    wait_for(vm.kiosk_active, timeout=40, interval=2, desc="coolbx-kiosk active")
    wait_for(vm.cdp_up, timeout=40, interval=2, desc="CDP-endpoint (poort 9222) op")
    # wacht tot er precies een renderbare page-target is
    wait_for(lambda: vm.cdp_page_count() >= 1, timeout=30, interval=2, desc="page-target")
    yield vm
    vm.kiosk_stop()
