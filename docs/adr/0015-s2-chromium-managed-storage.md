# ADR-0015: S2-spike — Chromium managed-storage + enforcement op Fedora (bevestigd)

- **Status:** Aanvaard
- **Datum:** 2026-06-23
- **Beslissers:** Johan, Claude

## Context
De minst-gedocumenteerde, meest risicovolle bouwsteen van het integratiecontract was: **levert
`chrome.storage.managed` (de `3rdparty`-managed-storage) wel aan op Fedora-RPM-Chromium?** Bewezen via een spike
met een lokale test-extensie (vaste ID via `key`) + een policy-JSON in `/etc/chromium/policies/managed/`.

## Bevindingen
- ✅ **Managed-storage levert aan (BEWEZEN, machine-leesbaar).** De extensie-service-worker las
  `chrome.storage.managed.get()` en de policy-waarden verschenen in de extensie-storage. Grep in
  `…/Local Extension Settings/<ID>/` vond zowel `serverUrl` (`focus-api.edugolo.be`) als `kioskMode`. Die strings
  kunnen alleen uit de gedelegeerde managed-waarde komen → de levering is bevestigd.
- ✅ **Enforcement-policies gelden** (transitief): `DeveloperToolsAvailability`, `URLBlocklist`,
  `IncognitoModeAvailability` staan in hetzelfde policy-bestand dat aantoonbaar geparst wordt (de `3rdparty`-key
  eruit werkte). Het zijn bovendien standaard Chromium-enterprise-policies. Exacte gedragsverificatie volgt in Fase 2/4.

## Kiosk-lessen (voor Fase 2/3 — waardevol)
- Chromium-binary op Fedora = **`/usr/bin/chromium-browser`**; managed-policy-pad = `/etc/chromium/policies/managed/`.
- **`--password-store=basic` is nodig in de kiosk** — anders blokkeert een gnome-keyring-dialoog het scherm.
- **`URLBlocklist: ["*"]` blokkeert álles** incl. `chrome://` en extensie-pagina's → de echte kiosk-policy moet de
  Focus-domeinen + benodigde extensie-resources **nauwkeurig allowlisten**; een wildcard `chrome-extension://*` in
  `URLAllowlist` overrulet de blocklist **niet** (filter-syntax).
- Directe navigatie naar een extensie-pagina vereist **`web_accessible_resources`** (relevant voor hoe de kiosk-URL gestructureerd wordt).
- Fedora levert een default **`disable-ai.json`**-policy; onze policy co-existeert ermee.

## Gevolgen
Het kern-integratiecontract (managed-storage) is technisch bevestigd op de gekozen base (fedora-bootc). **Force-install
via `update.xml`/`.crx` blijft een externe gate** (Focus-team levert de ondertekende `.crx` + bereikbare `update.xml`)
— uit te werken in Fase 2.

## Alternatieven
n.v.t. — dit is een spike-bevinding, geen keuze.
