"""Laag B — systeemstaat na boot (SSH-CLI-asserts; geen pixels). De goedkoopste, minst brosse laag."""


def test_gdm_active(vm):
    assert vm.ssh_ok("systemctl is-active --quiet gdm")


def test_networkmanager_active(vm):
    assert vm.ssh_ok("systemctl is-active --quiet NetworkManager")


def test_default_target_graphical(vm):
    assert vm.ssh("systemctl get-default").strip() == "graphical.target"


def test_gnome_shell_running(vm):
    assert vm.ssh_ok("pgrep -x gnome-shell")


def test_no_failed_units(vm):
    failed = vm.ssh("systemctl --failed --no-legend --plain 2>/dev/null || true").strip()
    assert failed == "", f"gefaalde units:\n{failed}"


def test_locale_nl_be(vm):
    assert "nl_BE" in vm.ssh("cat /etc/locale.conf")


def test_chromium_present(vm):
    assert "chromium" in vm.ssh("command -v chromium-browser chromium 2>/dev/null || true")


def test_kiosk_unit_files_present(vm):
    # de kiosk-launch + sway-config + managed policy moeten in de image zitten
    for f in (
        "/usr/bin/coolbx-kiosk-start",
        "/usr/share/coolbx/kiosk/chromium-kiosk.sh",
        "/usr/share/coolbx/kiosk/sway.conf",
        "/etc/chromium/policies/managed/coolbx-managed.json",
    ):
        assert vm.ssh_ok(f"test -f {f}"), f"ontbreekt: {f}"
