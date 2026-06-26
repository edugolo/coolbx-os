"""Fase 6 — ansible-pull vlootconfig (per rol, strak gescoped). SSH-state-checks.

De volledige pull→apply→idempotent-mechaniek is handmatig bewezen (changed=1 → changed=0, marker
met groep=leerlingen). Deze tests bewaken de statische opzet + de veilige no-op-default.
"""


def test_ansible_pull_present(vm):
    assert vm.ssh_ok("command -v ansible-pull")


def test_pull_timer_enabled(vm):
    assert vm.ssh_ok("systemctl is-enabled --quiet coolbx-ansible-pull.timer")


def test_laptop_group_default_leerlingen(vm):
    assert vm.ssh("cat /usr/share/coolbx/ansible/laptop-group").strip() == "leerlingen"


def test_pull_config_present(vm):
    assert vm.ssh_ok("test -f /etc/coolbx/ansible.conf")


def test_puller_noop_when_unconfigured(vm):
    # Veilige default: met de PLACEHOLDER-URL doet de puller niets (exit 0) en maakt geen marker —
    # zo breekt een onge­configureerd toestel niet.
    vm.ssh_sudo("rm -f /tmp/coolbx-ansible-marker", check=False)
    out = vm.ssh_sudo("/usr/libexec/coolbx-ansible-pull; echo rc=$?", check=False)
    assert "rc=0" in out
    assert "overslaan" in out  # de no-op-melding
    assert not vm.ssh_ok("test -f /tmp/coolbx-ansible-marker")


def test_pull_is_strictly_runtime_scoped(vm):
    # STRAK GESCOPED (roadmap): de puller mag geen software/kernconfig aanraken — het script
    # roept enkel ansible-pull aan met de groep-var, geen dnf/rpm/bootc.
    src = vm.ssh("cat /usr/libexec/coolbx-ansible-pull")
    code = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))
    for forbidden in ("dnf", "rpm ", "bootc", "rpm-ostree"):
        assert forbidden not in code, f"puller raakt {forbidden!r} aan (niet strak gescoped)"
