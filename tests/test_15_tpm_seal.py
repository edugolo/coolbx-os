"""B3.e — TPM2-sealed device-secret + toestelklasse (F-03-006).

De dev-VM draait met een swtpm-vTPM (Justfile). Bewijst:
  - de gast ziet een TPM2 en systemd-creds kan hem gebruiken;
  - het secret leeft uitsluitend TPM2-sealed op schijf (geen plaintext);
  - toestelklasse = tpm-sealed (klasse-bestand + coolbx-enroll-info);
  - de attest-keten werkt end-to-end met het sealed secret: het harnas
    verifieert de HMAC-handtekening ZELF met het via enroll-info verkregen
    secret (echte crypto-check, geen mock);
  - upgrade-pad: een bestaand plain secret wordt in-place geseald met behoud
    van waarde (de server-registratie blijft geldig) en de plaintext wordt
    vernietigd. (Mutaties draaien in de -snapshot-VM en verdwijnen na de run.)

FDE hoort bij het hardware-installatiepad (bootc install --block-setup
tpm2-luks, docs/ATTESTATION.md) — de dev-qcow2 heeft geen LUKS; enroll-info
rapporteert dat eerlijk (fde=false).
"""
import hashlib
import hmac
import json

from harness import wait_for


def _enroll_info(vm):
    out = vm.ssh_sudo("coolbx-enroll-info")
    return json.loads(out.strip().splitlines()[-1])


def test_gast_heeft_tpm2(vm):
    assert vm.ssh_ok("test -e /dev/tpmrm0 || test -e /dev/tpm0"), \
        "geen TPM-device in de gast — swtpm-flags kwijt in de Justfile?"
    ok = vm.ssh_sudo("systemd-creds has-tpm2 >/dev/null 2>&1 && echo ok || echo nok").strip()
    assert ok == "ok", "systemd-creds kan de TPM2 niet gebruiken"


def test_secret_sealed_geen_plaintext(vm):
    assert vm.ssh_sudo("test -s /etc/coolbx/device-secret.cred && echo ja || echo nee").strip() == "ja", \
        "geen sealed credential — draaide coolbx-device-secret.service?"
    assert vm.ssh_sudo("test -e /etc/coolbx/device-secret && echo ja || echo nee").strip() == "nee", \
        "plaintext-secret bestaat nog naast het sealed credential"
    assert vm.ssh("cat /etc/coolbx/device-class").strip() == "tpm-sealed"


def test_attest_hmac_verifieerbaar_met_enroll_secret(vm):
    info = _enroll_info(vm)
    assert info["deviceClass"] == "tpm-sealed"
    assert info["fde"] is False  # dev-qcow2 zonder LUKS; FDE = install-pad
    assert info["secret"]

    r = vm.attest_sign("tpm-seal-nonce-42")
    assert "error" not in r, f"tekenen faalde: {r}"
    expected = hmac.new(
        info["secret"].encode(),
        ("tpm-seal-nonce-42|" + r["session"]).encode(),
        hashlib.sha256,
    ).hexdigest()
    assert r["signature"] == expected, "HMAC verifieert niet met het enroll-secret"
    assert r["deviceId"] == info["deviceId"]


def test_upgrade_pad_plain_naar_sealed(vm):
    # Simuleer een pre-B3.e-toestel: plain secret, geen credential.
    vm.ssh_sudo(
        "systemctl stop coolbx-attestd; "
        "rm -f /etc/coolbx/device-secret.cred /etc/coolbx/device-class; "
        "umask 077; printf %s upgrade-test-secret > /etc/coolbx/device-secret; "
        "chmod 600 /etc/coolbx/device-secret"
    )
    vm.ssh_sudo("systemctl restart coolbx-device-secret.service && systemctl start coolbx-attestd")
    wait_for(lambda: vm.ssh_ok("test -S /run/coolbx-attest.sock"), timeout=20, desc="attestd terug op")

    info = _enroll_info(vm)
    assert info["secret"] == "upgrade-test-secret", "secret-waarde niet behouden bij sealen"
    assert info["deviceClass"] == "tpm-sealed"
    assert vm.ssh_sudo("test -e /etc/coolbx/device-secret && echo ja || echo nee").strip() == "nee", \
        "plaintext niet vernietigd na upgrade-seal"

    # En de daemon tekent met het geseald secret (cache is vers na herstart).
    r = vm.attest_sign("upgrade-nonce")
    expected = hmac.new(
        b"upgrade-test-secret",
        ("upgrade-nonce|" + r["session"]).encode(),
        hashlib.sha256,
    ).hexdigest()
    assert r.get("signature") == expected
