"""Lokale simulatie van de Focus-server-verificatie (docs/FOCUS-HANDOFF.md).

Bewijst de VOLLEDIGE attestatie-round-trip zonder echte server: een mock-server enrollt het toestel
(secret + deviceId), stuurt een nonce, het toestel tekent via de attest-daemon, en de mock-server
verifieert + past de proctoring-gate toe. Dit is exact wat de Focus-server moet doen.
"""
import hashlib
import hmac

import pytest

NONCE = "focus-server-nonce-2c91f"


def _server_decision(allowlist, device_id, session, signature, nonce=NONCE):
    """De verificatielogica die Focus 1-op-1 kan overnemen."""
    secret = allowlist.get(device_id)
    if not secret:
        return "REJECT-unknown-device"
    expect = hmac.new(secret, (nonce + "|" + session).encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expect, signature):
        return "REJECT-bad-signature"
    return "ALLOW-proctored" if session == "kiosk" else "DENY-proctoring-free"


@pytest.fixture(scope="module")
def enrolled(vm):
    """Enrollment: de 'server' kent het secret + de deviceId van dit toestel."""
    secret = vm.ssh_sudo("cat /etc/coolbx/device-secret").strip().encode()
    did = vm.attest_sign(NONCE).get("deviceId")
    assert did, "kon deviceId niet ophalen"
    return {"allowlist": {did: secret}, "device_id": did}


def test_kiosk_session_allowed_for_proctoring(vm, enrolled):
    r = vm.attest_sign(NONCE, as_user="coolbx-kiosk")
    assert r.get("session") == "kiosk", r
    decision = _server_decision(enrolled["allowlist"], r["deviceId"], r["session"], r["signature"])
    assert decision == "ALLOW-proctored", decision


def test_free_session_rejected_for_proctoring(vm, enrolled):
    r = vm.attest_sign(NONCE)  # gewone (leerling-)sessie → free
    assert r.get("session") == "free", r
    # de signature is GELDIG (echt toestel), maar proctoring wordt geweigerd
    decision = _server_decision(enrolled["allowlist"], r["deviceId"], r["session"], r["signature"])
    assert decision == "DENY-proctoring-free", decision


def test_forged_kiosk_claim_rejected(vm, enrolled):
    # aanvaller pakt een ECHTE free-attestatie en claimt 'kiosk' naar de server
    r = vm.attest_sign(NONCE)  # session=free, signature dekt nonce|free
    decision = _server_decision(enrolled["allowlist"], r["deviceId"], "kiosk", r["signature"])
    assert decision == "REJECT-bad-signature", decision  # HMAC(nonce|kiosk) != HMAC(nonce|free)


def test_unknown_device_rejected(vm, enrolled):
    r = vm.attest_sign(NONCE, as_user="coolbx-kiosk")
    decision = _server_decision(enrolled["allowlist"], "0000onbekendtoestel0000", r["session"], r["signature"])
    assert decision == "REJECT-unknown-device", decision
