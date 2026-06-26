"""Fase 4 — beheerde-laptop hardening: klok-lockdown (examen-kritiek).

De server is de tijd-/deadline-autoriteit: NTP is geforceerd en een leerling kan de systeemtijd niet
wijzigen. (Brede dconf-lockdown vrije modus = productbeslissing, follow-up.)
"""


def test_ntp_forced_via_chrony(vm):
    assert vm.ssh_ok("systemctl is-active --quiet chronyd.service")


def test_ntp_enabled_in_timedatectl(vm):
    out = vm.ssh("timedatectl show -p NTP --value 2>/dev/null || timedatectl 2>/dev/null")
    assert "yes" in out.lower() or "ntp" in out.lower()


def test_timedate_polkit_rule_denies_non_admin(vm):
    # polkit-rules.d is root-only leesbaar → met sudo lezen
    rule = vm.ssh_sudo("cat /etc/polkit-1/rules.d/49-coolbx-timedate.rules")
    # weigert de tijd-acties voor niet-wheel
    assert "org.freedesktop.timedate1.set-time" in rule
    assert "org.freedesktop.timedate1.set-timezone" in rule
    assert 'isInGroup("wheel")' in rule
    assert "polkit.Result.NO" in rule


def test_student_cannot_set_time(vm):
    # als de testuser (zonder sudo, zoals een leerling) → set-time moet falen (polkit weigert
    # / geen auth-agent). Bewijst dat de tijd niet zomaar instelbaar is vanuit de sessie.
    rc_out = vm.ssh("timedatectl set-time '2000-01-01 00:00:00' 2>&1; echo rc=$?")
    assert "rc=0" not in rc_out, f"set-time slaagde onverwacht: {rc_out!r}"
