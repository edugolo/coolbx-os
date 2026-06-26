"""Fase 8 — observability: het lokale coolbx-status-overzicht voor schoolIT (geen open poort)."""


def test_status_command_present(vm):
    assert vm.ssh_ok("test -x /usr/bin/coolbx-status")


def test_status_runs_and_reports(vm):
    out = vm.ssh_sudo("coolbx-status")
    # de kernsecties moeten aanwezig zijn
    for label in ("OS-image", "Boot-status", "Update-timer", "Kiosk-launcher",
                  "Attestatie-daemon", "Gefaalde units"):
        assert label in out, f"sectie {label!r} ontbreekt in coolbx-status:\n{out}"


def test_status_no_open_admin_port(vm):
    # bewust GEEN Cockpit-poort 9090 standaard open op een toetstoestel
    out = vm.ssh_sudo("ss -ltn 2>/dev/null | grep ':9090' || echo DICHT", check=False)
    assert "DICHT" in out, "Cockpit-poort 9090 staat open (niet gewenst by default)"
