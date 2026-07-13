"""Native-messaging-naad end-to-end (Focus-audit F-06-010 / F-02-063).

De Focus↔OS-naad hing tot nu op een in-repo mock: test_12 praat rechtstreeks
met de daemon-socket en slaat zo de native-messaging-host + zijn stdin/stdout-
framing over. Dit oefent de ÉCHTE wire uit die Chromium gebruikt:
`coolbx-attest-host` gevoed met een 4-byte-LE-lengte-prefix + JSON op stdin, en
het lengte-geprefixte JSON-antwoord van stdout — helemaal door naar de root-
daemon (echt secret) met HMAC-verificatie. Het enige dat hier niet meedraait is
Chromium's eigen connectNative-plumbing (Chrome-code, geen Coolbx-code).

De host draait als de kiosk-user (kind van Chromium) → SO_PEERCRED-sessie=kiosk.
"""
import base64
import hashlib
import hmac
import json
import struct

import pytest

HOST = "/usr/libexec/coolbx-attest-host"
KIOSK_USER = "coolbx-kiosk"


def _frame(obj):
    body = json.dumps(obj).encode()
    return struct.pack("<I", len(body)) + body


def _unframe(raw):
    if len(raw) < 4:
        return None
    n = struct.unpack("<I", raw[:4])[0]
    return json.loads(raw[4:4 + n].decode())


def _native_call(vm, payload_bytes, as_user=KIOSK_USER):
    """Voed payload_bytes op stdin van de host (als de kiosk-user) en geef de
    ruwe stdout-bytes terug. Binair-veilig via base64 + een tmp-bestand, zodat
    de sudo-wachtwoord-stdin de payload-stdin niet opslokt."""
    b64_in = base64.b64encode(payload_bytes).decode()
    # Root (ssh_sudo) → sudo -u kiosk is passwordless; de host leest uit het
    # tmp-bestand, niet uit de (door -S opgeslokte) stdin.
    out_b64 = vm.ssh_sudo(
        f"printf %s {b64_in} | base64 -d > /tmp/nm-in && "
        f"sudo -u {as_user} {HOST} < /tmp/nm-in | base64 -w0; "
        f"rm -f /tmp/nm-in"
    ).strip()
    return base64.b64decode(out_b64) if out_b64 else b""


@pytest.fixture(scope="module")
def enroll_secret(vm):
    info = json.loads(vm.ssh_sudo("coolbx-enroll-info").strip().splitlines()[-1])
    return info


def test_challenge_roundtrip_through_host(vm, enroll_secret):
    nonce = "native-seam-nonce-7"
    raw = _native_call(vm, _frame({"challenge": nonce}))
    resp = _unframe(raw)
    assert resp, f"geen (geldig geframede) respons van de host: {raw!r}"
    assert resp["session"] == "kiosk", "host draaide niet als kiosk-peer"
    assert resp["deviceId"] == enroll_secret["deviceId"]
    # De handtekening is met het echte (mogelijk TPM-sealed) secret gezet en
    # verifieert met wat enrollment uitgeeft — de volledige naad, geen mock.
    expected = hmac.new(
        enroll_secret["secret"].encode(),
        (nonce + "|kiosk").encode(),
        hashlib.sha256,
    ).hexdigest()
    assert resp["signature"] == expected


def test_free_session_when_not_kiosk_peer(vm, enroll_secret):
    # Als een gewone user de host draait → SO_PEERCRED=free; de handtekening
    # bindt 'free' → een kiosk-only examen wordt server-side terecht geweigerd.
    raw = _native_call(vm, _frame({"challenge": "free-nonce"}), as_user="tester")
    resp = _unframe(raw)
    assert resp and resp["session"] == "free"
    expected = hmac.new(
        enroll_secret["secret"].encode(),
        ("free-nonce|free").encode(),
        hashlib.sha256,
    ).hexdigest()
    assert resp["signature"] == expected


def test_empty_stdin_yields_no_output(vm):
    # Chromium sluit soms de poort zonder bericht → 0 bytes stdin. De host mag
    # dan niets (en zeker geen kapotte frame) schrijven.
    assert _native_call(vm, b"") == b""


def test_oversized_length_prefix_rejected(vm):
    # Een lengte-prefix boven de 1 MiB-limiet → de host leest de body niet en
    # schrijft niets (geen geheugen-explosie, geen half frame).
    raw = _native_call(vm, struct.pack("<I", 5 * 1024 * 1024) + b"{}")
    assert raw == b""


def test_empty_challenge_returns_error_frame(vm):
    resp = _unframe(_native_call(vm, _frame({"challenge": ""})))
    assert resp and "error" in resp
