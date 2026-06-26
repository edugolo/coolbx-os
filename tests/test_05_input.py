"""Laag C — toetsenbord/veld-invoer. Bewijst dat de harness waarden in invoervelden kan zetten.

Twee paden (ADR-0020):
  - CDP `fill` (React/Vue-proof) → voor webformulier-velden in de Focus-extensie (examenantwoorden, login)
  - QMP-toetsenbord → voor native/shell-velden (niet hier getest; werkt op wat focus heeft)
"""


def test_cdp_fill_and_readback(kiosk):
    # Injecteer een testveld in de live kiosk-DOM.
    kiosk.cdp_eval(
        "(() => { let i = document.querySelector('#e2e-input');"
        " if (!i) { i = document.createElement('input'); i.id = 'e2e-input';"
        " document.body.appendChild(i); } i.value = ''; return true; })()"
    )
    # Vul het via de fill-API (native setter + events → framework-proof).
    res = kiosk.cdp_fill("#e2e-input", "leerling-antwoord-42")
    assert isinstance(res, dict) and res.get("ok") is True, f"fill faalde: {res}"
    assert res.get("value") == "leerling-antwoord-42"

    # Onafhankelijke read bevestigt dat de waarde echt in het veld staat.
    val = kiosk.cdp_eval("document.querySelector('#e2e-input').value")
    assert val == "leerling-antwoord-42"


def test_cdp_insert_text_into_focused(kiosk):
    # Focus een leeg veld en typ erin via Input.insertText (alsof getypt).
    kiosk.cdp_eval(
        "(() => { let i = document.querySelector('#e2e-typed');"
        " if (!i) { i = document.createElement('input'); i.id = 'e2e-typed';"
        " document.body.appendChild(i); } i.value = ''; i.focus(); return true; })()"
    )
    kiosk.cdp_type("hallo")
    val = kiosk.cdp_eval("document.querySelector('#e2e-typed').value")
    assert val == "hallo", f"insertText kwam niet aan: {val!r}"
