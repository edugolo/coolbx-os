"""Fase 2 — het integratiecontract end-to-end (force-install + managed-storage).

Bewijst tegen de LIVE Focus-dashboard dat Chromium:
  1. de productie student-extensie force-installeert (ExtensionSettings → status OK);
  2. de managed-storage aflevert (serverUrl + kioskMode, isExtension, status OK).

Vereist internet + bereikbare update.xml (de VM heeft NAT-net). Onbereikbaar =
HARD FALEN (F-06-011): een stil geskipte integratietest las jarenlang als "gedekt"
terwijl hij nooit draaide. Bewust offline ontwikkelen kan met een expliciete
escape: COOLBX_E2E_ALLOW_OFFLINE=1.
"""
import os

import pytest

from harness import wait_for

UPDATE_XML = "https://focus-dashboard.edugolo.be/extension-updates/update.xml"
SERVER_URL = "https://focus-api.edugolo.be"


@pytest.fixture(scope="module")
def _dashboard_reachable(vm):
    if not vm.ssh_ok(f"curl -sf -o /dev/null --max-time 10 {UPDATE_XML}"):
        if os.environ.get("COOLBX_E2E_ALLOW_OFFLINE") == "1":
            pytest.skip("Focus-dashboard onbereikbaar — expliciet toegestaan (COOLBX_E2E_ALLOW_OFFLINE=1)")
        pytest.fail(
            "Focus-dashboard onbereikbaar vanuit de VM — integratietest kan niet draaien. "
            "Bewust offline? Zet COOLBX_E2E_ALLOW_OFFLINE=1. (F-06-011: niet meer stil skippen)"
        )


def test_extension_settings_force_install_applied(kiosk, _dashboard_reachable):
    # Eén-keer-lezen-en-checken (geen dubbele read → geen flaky tussenstaat): wacht tot een
    # contract-snapshot ExtensionSettings mét status OK toont.
    c = wait_for(
        lambda: (lambda fc: fc if fc.get("ext_settings_status") == "OK" else None)(
            kiosk.focus_contract()
        ),
        timeout=40, interval=2, desc="ExtensionSettings status OK",
    )
    assert c["ext_settings_status"] == "OK"


def test_managed_storage_delivered(kiosk, _dashboard_reachable):
    # De tmpfs-kioskhome her-downloadt de .crx per sessie → force-install + policy-associatie
    # kan ~20-60s duren. Ruime timeout zodat de integratietest niet flaket in de volle suite.
    contract = wait_for(
        lambda: (kiosk.focus_contract().get("server_url") and kiosk.focus_contract()),
        timeout=120, interval=4, desc="managed-storage (serverUrl) afgeleverd",
    )
    assert contract["server_url"] == SERVER_URL
    assert contract["managed_status"] == "OK"
    # kioskMode staat BEWUST niet meer in de globale managed-storage (ADR-0024): het kiosk-signaal
    # is voortaan de per-sessie attest-claim (session=kiosk), niet een globale vlag.
    assert contract["kiosk_mode"] is None
