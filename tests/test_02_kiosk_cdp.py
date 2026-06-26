"""Laag C — de kiosk-Chromium via CDP. De betrouwbaarste GUI-assert: échte browserstaat, geen pixels.

Gebruikt de session-scoped `kiosk`-fixture (debug-kiosk met CDP-poort 9222 open).
"""


def test_cdp_endpoint_reachable(kiosk):
    targets = kiosk.cdp("targets")
    assert isinstance(targets, str) and "page" in targets


def test_single_window_no_handoff_stack(kiosk):
    # regressie op de singleton-handoff-bug: elk --app-venster = 1 CDP page-target.
    # De stapel manifesteerde zich als meerdere page-targets in één proces.
    assert kiosk.cdp_page_count() == 1, "meerdere page-targets (handoff-venster-stapel terug?)"


def test_page_title(kiosk):
    assert kiosk.cdp("title") == "Coolbx Focus — Toetsmodus"


def test_page_is_placeholder(kiosk):
    info = kiosk.cdp_eval(
        "JSON.stringify({url: location.href, body: document.body.innerText})"
    )
    import json
    d = json.loads(info)
    assert d["url"].endswith("/placeholder.html")
    assert "Toetsmodus" in d["body"]


# (De managed-storage wordt nu robuust geverifieerd tegen de echte extensie in
#  test_06_focus_contract.py via chrome://policy — zie ADR-0021. De vroegere placeholder
#  hier ("faalt netjes zonder extensie") is achterhaald nu Fase 2 force-install werkt.)


def test_policy_oracle_reads_applied_state(kiosk):
    pols = kiosk.cdp("policy")
    assert isinstance(pols, list)
    names = {p.get("name") for p in pols}
    # onze uitgerolde coolbx-managed.json bevat een _comment-veld → zichtbaar als gezet beleid
    assert "_comment" in names, f"verwacht _comment in toegepaste policies, kreeg: {names}"
