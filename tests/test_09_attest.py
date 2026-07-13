"""Fase: toestel-attestatie — HMAC-handshake (ADR-0013, docs/ATTESTATION.md).

Verifieert de OS-kant van de anti-spoofing: per-toestel-secret (root-only), signing-daemon die tekent
zonder het secret te lekken, en de native-messaging-host-manifest met de exacte Focus-extensie-ID.
"""
import re

EXT_ID = "makdakigkdbicdljgdclgnejachcohag"


def test_device_secret_is_root_only(vm):
    # B3.e: op een TPM-toestel (de dev-VM heeft swtpm) is het secret TPM2-sealed
    # (.cred) en bestaat er GEEN plaintext meer; zonder TPM is het een plain
    # file. Beide vormen zijn 0600 root en voor de leerling-sessie onleesbaar.
    sealed = vm.ssh_sudo("test -s /etc/coolbx/device-secret.cred && echo ja || echo nee").strip() == "ja"
    path = "/etc/coolbx/device-secret.cred" if sealed else "/etc/coolbx/device-secret"
    assert not vm.ssh_ok(f"test -r {path} && cat {path}")
    perms = vm.ssh_sudo(f"stat -c '%a %U' {path}").strip()
    assert perms == "600 root", f"secret-perms fout: {perms!r}"
    if sealed:
        # géén plaintext-restant naast het sealed credential
        assert vm.ssh_sudo("test -e /etc/coolbx/device-secret && echo ja || echo nee").strip() == "nee"


def test_attestd_active_and_socket(vm):
    assert vm.ssh_ok("systemctl is-active --quiet coolbx-attestd.service")
    assert vm.ssh_ok("test -S /run/coolbx-attest.sock")


def test_daemon_signs_challenge(vm):
    r = vm.attest_sign("server-nonce-abc123")
    assert "error" not in r, f"tekenen faalde: {r}"
    # HMAC-SHA256 hex = 64 tekens; deviceId + session aanwezig
    assert re.fullmatch(r"[0-9a-f]{64}", r.get("signature", "")), r
    assert r.get("deviceId")
    assert r.get("session") in ("kiosk", "free")


def test_no_replay_different_challenge_different_signature(vm):
    a = vm.attest_sign("nonce-een")
    b = vm.attest_sign("nonce-twee")
    assert a.get("signature") and b.get("signature")
    assert a["signature"] != b["signature"]
    assert a["deviceId"] == b["deviceId"]  # zelfde toestel → zelfde deviceId


def test_session_claim_free_for_regular_user(vm):
    # de gewone (leerling-)sessie → session=free (geen proctoring-recht)
    r = vm.attest_sign("nonce-free")
    assert r.get("session") == "free", r


def test_session_claim_kiosk_for_kiosk_user(vm):
    # verbinden ALS de coolbx-kiosk-user → session=kiosk (peer-cred, onvervalsbaar)
    r = vm.attest_sign("nonce-kiosk", as_user="coolbx-kiosk")
    assert "error" not in r, f"tekenen als kiosk-user faalde: {r}"
    assert r.get("session") == "kiosk", r
    # de signature moet de session-claim dekken: kiosk-sig != free-sig voor dezelfde nonce
    free = vm.attest_sign("nonce-kiosk")
    assert r["signature"] != free["signature"], "session wordt niet meegetekend (vervalsbaar!)"


def test_native_messaging_manifest(vm):
    import json
    raw = vm.ssh("cat /etc/chromium/native-messaging-hosts/be.edugolo.coolbx.attest.json")
    m = json.loads(raw)
    assert m["path"] == "/usr/libexec/coolbx-attest-host"
    assert m["type"] == "stdio"
    # allowed_origins moet EXACT de Focus-extensie zijn (geen wildcard)
    assert m["allowed_origins"] == [f"chrome-extension://{EXT_ID}/"]
