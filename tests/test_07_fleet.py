"""Fase 5 — fleet-laag: staged auto-update + greenboot-health (SSH-state, geen CDP).

Verifieert dat de OTA-update veilig is opgezet (stage-only, off-hours, default gemaskeerd) en dat
de greenboot-health-check lokaal slaagt op een gezonde boot.
"""


def test_default_apply_timer_masked(vm):
    # de default fetch-apply-timer kan op willekeurig moment applyen/rebooten → gemaskeerd
    out = vm.ssh("systemctl is-enabled bootc-fetch-apply-updates.timer 2>&1 || true")
    assert "masked" in out, f"default apply-timer niet gemaskeerd: {out!r}"


def test_staged_update_timer_enabled(vm):
    assert vm.ssh_ok("systemctl is-enabled --quiet coolbx-update.timer")


def test_update_is_stage_only_no_apply(vm):
    # de update-service mag STAGEN (bootc upgrade) maar nooit --apply/reboot uitlokken.
    # Check de ECHTE ExecStart-directives (niet de uitleg-comments die 'reboot' noemen).
    unit = vm.ssh("systemctl cat coolbx-update.service")
    execs = [l for l in unit.splitlines() if l.strip().startswith("Exec")]
    assert any("bootc upgrade" in l for l in execs)
    assert all("--apply" not in l for l in execs)
    assert not any("reboot" in l.lower() for l in execs)


def test_greenboot_health_check_passes(vm):
    # de lokale health-check moet GROEN zijn op een gezonde boot (exit 0)
    assert vm.ssh_ok(
        "echo tester | sudo -S /etc/greenboot/check/required.d/50-coolbx-kiosk-health.sh"
    )


def test_greenboot_health_is_local_only(vm):
    # cruciale eigenschap (ADR-0017): NOOIT focus-api in de health-check (externe outage zou de
    # hele vloot doen terugrollen). Negeer comment-regels (die noemen focus-api uitleggend).
    src = vm.ssh("cat /etc/greenboot/check/required.d/50-coolbx-kiosk-health.sh")
    code = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))
    assert "focus-api" not in code and "edugolo" not in code
