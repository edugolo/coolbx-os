"""Per-examen kiosk-policy (B3.c, Focus-audit F-03-007).

De Focus-server stuurt bij examen-start een allowlist naar de extensie in de kiosk; die relayt naar
coolbx-attestd (native host), en alleen een KIOSK-peer (SO_PEERCRED) mag de Chromium-policy laten
schrijven. Dit bewijst de OS-kant van de keten: peer-afdwinging, domein-validatie, default-deny
(URLBlocklist "*"), infra-baseline, lobby-herstel en opruiming (kiosk-einde/boot).
"""
import json

import pytest

from harness import SSH_PASS

POLICY = "/etc/chromium/policies/managed/coolbx-exam.json"


def _daemon_request(vm, payload, as_user=None):
    """Stuur een willekeurige JSON-request naar de attest-daemon (unix-socket)."""
    py = (
        "import socket,json,sys;"
        "s=socket.socket(socket.AF_UNIX);s.settimeout(30);s.connect('/run/coolbx-attest.sock');"
        "s.sendall(sys.argv[1].encode()+b'\\n');"
        "sys.stdout.write(s.recv(8192).decode())"
    )
    client = f"python3 -c {json.dumps(py)} {json.dumps(json.dumps(payload))}"
    if as_user:
        cmd = f"echo {SSH_PASS} | sudo -S -u {as_user} {client}"
    else:
        cmd = client
    out = vm.ssh(cmd)
    try:
        return json.loads(out.strip().splitlines()[-1])
    except (json.JSONDecodeError, ValueError, IndexError):
        return {"error": out.strip()}


def _read_policy(vm):
    out = vm.ssh_sudo(f"cat {POLICY} 2>/dev/null || echo AFWEZIG").strip()
    if out == "AFWEZIG":
        return None
    return json.loads(out)


@pytest.fixture(autouse=True)
def _schone_policy(vm):
    """Elke test start en eindigt zonder achtergebleven policy-bestand."""
    vm.ssh_sudo("/usr/libexec/coolbx-exam-policy clear")
    yield
    vm.ssh_sudo("/usr/libexec/coolbx-exam-policy clear")


def test_statics_aanwezig(vm):
    assert vm.ssh_ok("test -x /usr/libexec/coolbx-exam-policy")
    assert vm.ssh_ok("test -r /etc/coolbx/focus-infra.domains")
    enabled = vm.ssh("systemctl is-enabled coolbx-exam-policy-cleanup.service || true").strip()
    assert enabled == "enabled", enabled


def test_free_peer_mag_geen_policy_zetten(vm):
    r = _daemon_request(vm, {"examPolicy": {"phase": "exam", "allowDomains": ["evil.example"]}})
    assert "error" in r and "kiosk" in r["error"], r
    assert _read_policy(vm) is None, "free-peer schreef tóch een policy"


def test_kiosk_peer_schrijft_examen_policy(vm):
    r = _daemon_request(
        vm,
        {"examPolicy": {"phase": "exam", "allowDomains": [
            "docs.google.com",
            "*.school.be",
            "Bad Entry!",           # moet geweigerd worden (validatie)
            "javascript:alert(1)",  # idem
        ]}},
        as_user="coolbx-kiosk",
    )
    assert r.get("ok") is True, r
    policy = _read_policy(vm)
    assert policy is not None
    assert policy["URLBlocklist"] == ["*"]  # default-deny
    allow = policy["URLAllowlist"]
    assert "docs.google.com" in allow
    assert "school.be" in allow              # *.x → kale domein (subdomein-inclusief)
    assert "focus-dashboard.edugolo.be" in allow  # infra-baseline
    assert any(e.startswith("chrome-extension://") for e in allow)
    assert not any("Bad" in e or "javascript" in e for e in allow)
    # Examen-hardeningset aanwezig.
    assert policy["DownloadRestrictions"] == 3
    assert policy["PrintingEnabled"] is False


def test_lobby_fase_herstelt_default_deny_baseline(vm):
    ok = _daemon_request(
        vm, {"examPolicy": {"phase": "exam", "allowDomains": ["docs.google.com"]}}, as_user="coolbx-kiosk"
    )
    assert ok.get("ok") is True, ok
    r = _daemon_request(vm, {"examPolicy": {"phase": "lobby", "allowDomains": []}}, as_user="coolbx-kiosk")
    assert r.get("ok") is True, r
    policy = _read_policy(vm)
    assert policy is not None
    assert policy["URLBlocklist"] == ["*"]
    assert "docs.google.com" not in policy["URLAllowlist"]  # les-domein weg
    assert "focus-dashboard.edugolo.be" in policy["URLAllowlist"]  # infra blijft


def test_attest_challenge_blijft_werken_naast_exam_op(vm):
    """De protocol-uitbreiding mag het bestaande attest-pad niet breken."""
    r = vm.attest_sign("regressie-nonce-13")
    assert r.get("session") in ("kiosk", "free"), r
    assert r.get("signature"), r
